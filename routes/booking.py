from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from datetime import datetime, date, time, timedelta
from models import db, Business, Service, WorkingHours, Appointment
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

booking_bp = Blueprint('booking', __name__)

def get_cancel_token(appt_id):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'appt_id': appt_id}, salt='cancel-appt')

def verify_cancel_token(token, max_age=60*60*24*7):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token, salt='cancel-appt', max_age=max_age)
        return data.get('appt_id')
    except (BadSignature, SignatureExpired):
        return None

def send_confirmation_email(appt, business):
    if not business.send_confirmation:
        return
    if not appt.customer_email:
        return
    if not current_app.config.get('MAIL_USERNAME'):
        return
    try:
        from flask_mail import Message
        from app import mail
        cancel_url = url_for('booking.cancel_appointment', token=get_cancel_token(appt.id), _external=True)
        greeting = (business.email_greeting or '').replace('{nombre}', appt.customer_name)
        accent = business.email_accent_color or '#000000'
        r, g, b = int(accent[1:3],16), int(accent[3:5],16), int(accent[5:7],16)
        header_text = '#ffffff' if (0.299*r+0.587*g+0.114*b)/255 < 0.5 else '#000000'
        html_body = render_template('email/confirmation.html',
            subject=business.email_subject or 'Tu reserva ha sido recibida',
            biz_name=business.name,
            logo_url=request.host_url.rstrip('/')+business.logo_url if business.logo_url else None,
            biz_address=business.address or '',
            greeting=greeting,
            footer_msg=business.email_footer_msg or '',
            service_name=appt.service.name if appt.service else '',
            appt_date=appt.date.strftime('%A %d de %B de %Y') if appt.date else '',
            appt_time=appt.time.strftime('%H:%M') if appt.time else '',
            cancel_url=cancel_url,
            accent=accent,
            header_text=header_text,
            email_bg=business.email_bg_color or '#f0f2f5',
        )
        msg = Message(
            subject=business.email_subject or f'Reserva en {business.name} confirmada',
            recipients=[appt.customer_email],
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f'Email cliente no enviado: {e}')

def notify_staff(appt):
    """Notifica al colaborador cuando le hacen una reserva."""
    if not appt.staff or not appt.staff.email:
        return
    if not current_app.config.get('MAIL_USERNAME'):
        return
    try:
        from flask_mail import Message
        from app import mail
        precio = appt.service.price_display() if appt.service else 'No especificado'
        html = (
            '<div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:20px">'
            '<div style="background:#111827;padding:20px;border-radius:12px 12px 0 0;text-align:center">'
            f'<h2 style="color:#fff;margin:0;font-size:18px">Nueva reserva 📅</h2>'
            '</div>'
            '<div style="background:#fff;padding:24px;border-radius:0 0 12px 12px;border:1px solid #e5e7eb;border-top:none">'
            f'<p style="font-size:15px;margin:0 0 16px">Hola <b>{appt.staff.name}</b>, tienes una nueva cita:</p>'
            '<div style="background:#f8f9fa;border-radius:8px;padding:16px;margin-bottom:16px">'
            f'<p style="margin:6px 0"><b>👤 Cliente:</b> {appt.customer_name}</p>'
            f'<p style="margin:6px 0"><b>📱 Teléfono:</b> {appt.customer_phone or "No indicado"}</p>'
            f'<p style="margin:6px 0"><b>✉️ Email:</b> {appt.customer_email or "No indicado"}</p>'
            + (f'<p style="margin:6px 0"><b>⚡ Servicio:</b> {appt.service.name}</p>' if appt.service else '')
            + (f'<p style="margin:6px 0"><b>💰 Precio:</b> {precio}</p>' if appt.service else '')
            + (f'<p style="margin:6px 0"><b>📅 Fecha:</b> {appt.date.strftime("%d/%m/%Y")}</p>' if appt.date else '')
            + (f'<p style="margin:6px 0"><b>🕐 Hora:</b> {appt.time.strftime("%H:%M")}</p>' if appt.time else '')
            + (f'<p style="margin:6px 0"><b>📝 Notas:</b> {appt.notes}</p>' if appt.notes else '')
            + '</div>'
            '<p style="color:#6b7280;font-size:13px;margin:0">¡Que te vaya bien con la cita!</p>'
            '<hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">'
            '<p style="font-size:11px;color:#9ca3af;text-align:center">Revyo · Made by Nouqty</p>'
            '</div></div>'
        )
        hora = appt.time.strftime('%H:%M') if appt.time else ''
        msg = Message(
            subject=f'📅 Nueva cita — {appt.customer_name} a las {hora}',
            recipients=[appt.staff.email],
            html=html,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        current_app.logger.info(f'Notif colaborador enviada a {appt.staff.email}')
    except Exception as e:
        current_app.logger.warning(f'Email colaborador no enviado: {e}')

def get_available_slots(business, target_date):
    weekday = target_date.weekday()
    wh = WorkingHours.query.filter_by(business_id=business.id, day_of_week=weekday).first()
    if not wh or wh.is_closed:
        return []
    slots = []
    current = datetime.combine(target_date, wh.open_time)
    end     = datetime.combine(target_date, wh.close_time)
    delta   = timedelta(minutes=business.slot_duration_min)
    booked  = {
        str(a.time)[:5]
        for a in Appointment.query.filter(
            Appointment.business_id == business.id,
            Appointment.date == target_date,
            Appointment.status.in_(['pending', 'confirmed'])
        ).all()
    }
    now  = datetime.now()
    lead = timedelta(hours=business.booking_lead_hours)
    while current < end:
        slot_str  = current.strftime('%H:%M')
        available = slot_str not in booked and datetime.combine(target_date, current.time()) > now + lead
        slots.append({'time': slot_str, 'available': available})
        current += delta
    return slots

@booking_bp.route('/b/<slug>')
def page(slug):
    from models import Staff
    business = Business.query.filter_by(slug=slug, is_active=True).first_or_404()
    services = business.services.filter_by(is_active=True).order_by(Service.order, Service.id).all()
    staff    = Staff.query.filter_by(business_id=business.id, is_active=True).all()
    today    = date.today()
    available_dates = []
    for i in range(business.max_advance_days + 1):
        d  = today + timedelta(days=i)
        wh = WorkingHours.query.filter_by(business_id=business.id, day_of_week=d.weekday()).first()
        if wh and not wh.is_closed:
            available_dates.append(d.strftime('%Y-%m-%d'))
    return render_template('booking/page.html', business=business,
                           services=services, staff=staff, available_dates=available_dates)

@booking_bp.route('/b/<slug>/slots')
def slots(slug):
    business = Business.query.filter_by(slug=slug, is_active=True).first_or_404()
    try:
        target_date = datetime.strptime(request.args.get('date',''), '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])
    return jsonify(get_available_slots(business, target_date))

@booking_bp.route('/b/<slug>/book', methods=['POST'])
def book(slug):
    business = Business.query.filter_by(slug=slug, is_active=True).first_or_404()

    customer_name  = request.form.get('customer_name', '').strip()
    customer_email = request.form.get('customer_email', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    service_id     = request.form.get('service_id', '').strip()
    staff_id       = request.form.get('staff_id', '').strip()
    date_str       = request.form.get('date', '')
    time_str       = request.form.get('time', '')
    notes          = request.form.get('notes', '').strip()

    current_app.logger.info(f'Booking: customer={customer_name} staff_id={staff_id} date={date_str} time={time_str}')

    errors = []
    if not customer_name: errors.append('El nombre es requerido')
    if not date_str:      errors.append('La fecha es requerida')
    if not time_str:      errors.append('El horario es requerido')

    appt_date = appt_time = None
    try:
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appt_time = datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        if not errors: errors.append('Fecha u hora inválida')

    if appt_date and appt_time:
        conflict = Appointment.query.filter(
            Appointment.business_id == business.id,
            Appointment.date == appt_date,
            Appointment.time == appt_time,
            Appointment.status.in_(['pending', 'confirmed'])
        ).first()
        if conflict:
            errors.append('Ese horario ya fue reservado. Elige otro.')

    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('booking.page', slug=slug))

    duration = business.slot_duration_min
    svc = None
    if service_id:
        svc = Service.query.filter_by(id=service_id, business_id=business.id).first()
        if svc:
            duration = svc.duration_min

    # Resolver staff_id
    final_staff_id = None
    if staff_id and staff_id.isdigit():
        final_staff_id = int(staff_id)

    appt = Appointment(
        business_id=business.id,
        service_id=int(service_id) if service_id and service_id.isdigit() else None,
        staff_id=final_staff_id,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        date=appt_date,
        time=appt_time,
        duration_min=duration,
        notes=notes,
        status='pending'
    )
    db.session.add(appt)
    db.session.commit()

    current_app.logger.info(f'Reserva guardada: ID={appt.id} staff_id={appt.staff_id}')

    send_confirmation_email(appt, business)
    notify_staff(appt)

    return redirect(url_for('booking.confirmation', slug=slug, appt_id=appt.id))

@booking_bp.route('/b/<slug>/confirmacion/<int:appt_id>')
def confirmation(slug, appt_id):
    business = Business.query.filter_by(slug=slug).first_or_404()
    appt     = Appointment.query.filter_by(id=appt_id, business_id=business.id).first_or_404()
    return render_template('booking/confirmation.html', business=business, appt=appt)

@booking_bp.route('/cancelar/<token>')
def cancel_appointment(token):
    appt_id = verify_cancel_token(token)
    if not appt_id:
        flash('El enlace de cancelación ha expirado o no es válido.', 'error')
        return redirect('/')
    appt = Appointment.query.get(appt_id)
    if not appt:
        flash('La reserva no fue encontrada.', 'error')
        return redirect('/')
    business = appt.business
    if appt.status in ('cancelled', 'completed'):
        flash(f'Esta reserva ya está {appt.status}.', 'info')
        return redirect(url_for('booking.page', slug=business.slug))
    return render_template('booking/cancel_confirm.html', appt=appt, business=business, token=token)

@booking_bp.route('/cancelar/<token>/confirmar', methods=['POST'])
def cancel_appointment_confirm(token):
    appt_id = verify_cancel_token(token)
    if not appt_id:
        flash('Enlace inválido o expirado.', 'error')
        return redirect('/')
    appt = Appointment.query.get(appt_id)
    if appt and appt.status not in ('cancelled', 'completed'):
        appt.status = 'cancelled'
        db.session.commit()
        flash('Tu reserva ha sido cancelada correctamente.', 'success')
        return redirect(url_for('booking.page', slug=appt.business.slug))
    return redirect('/')
