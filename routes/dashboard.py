from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, time, timedelta
from models import db, Business, Service, Staff, WorkingHours, Appointment
import os
import re

dashboard_bp = Blueprint('dashboard', __name__)

def require_active_subscription(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.has_active_subscription:
            flash('Tu suscripción no está activa. Por favor suscríbete para continuar.', 'warning')
            return redirect(url_for('payment.plans'))
        return f(*args, **kwargs)
    return decorated


@dashboard_bp.route('/dashboard')
@login_required
def index():
    business = current_user.business
    if not business:
        return redirect(url_for('dashboard.setup'))

    # Estadísticas
    today = date.today()
    week_ago = today - timedelta(days=7)

    total_appointments = business.appointments.count()
    today_appointments = business.appointments.filter(
        Appointment.date == today,
        Appointment.status != 'cancelled'
    ).all()
    pending_count = business.appointments.filter_by(status='pending').count()
    this_week = business.appointments.filter(
        Appointment.date >= week_ago,
        Appointment.status != 'cancelled'
    ).count()

    # Próximas citas
    upcoming = business.appointments.filter(
        Appointment.date >= today,
        Appointment.status.in_(['pending', 'confirmed'])
    ).order_by(Appointment.date, Appointment.time).limit(10).all()

    return render_template('dashboard/index.html',
                           business=business,
                           today_appointments=today_appointments,
                           upcoming=upcoming,
                           total_appointments=total_appointments,
                           pending_count=pending_count,
                           this_week=this_week)


@dashboard_bp.route('/dashboard/customize', methods=['GET', 'POST'])
@login_required
@require_active_subscription
def customize():
    business = current_user.business

    if request.method == 'POST':
        # Datos básicos
        business.name        = request.form.get('name', business.name).strip()
        business.description = request.form.get('description', '').strip()
        business.category    = request.form.get('category', 'general')
        business.phone       = request.form.get('phone', '').strip()
        business.address     = request.form.get('address', '').strip()
        business.instagram   = request.form.get('instagram', '').strip()
        business.whatsapp    = request.form.get('whatsapp', '').strip()

        # Colores y fuente
        business.primary_color   = request.form.get('primary_color', business.primary_color)
        business.secondary_color = request.form.get('secondary_color', business.secondary_color)
        business.accent_color    = request.form.get('accent_color', business.accent_color)
        business.text_color      = request.form.get('text_color', business.text_color)
        business.font_choice     = request.form.get('font_choice', 'Syne')
        business.dark_bg_color   = request.form.get('dark_bg_color', business.dark_bg_color or '#0f0f1a')
        business.dark_card_color = request.form.get('dark_card_color', business.dark_card_color or '#1a1a2e')
        business.button_style    = request.form.get('button_style', 'rounded')
        business.card_style      = request.form.get('card_style', 'elevated')
        business.header_style    = request.form.get('header_style', 'gradient')
        business.allow_dark_mode = request.form.get('allow_dark_mode') == 'on'

        # Configuración de reservas
        try:
            business.booking_lead_hours = int(request.form.get('booking_lead_hours', 1))
            business.max_advance_days   = int(request.form.get('max_advance_days', 30))
            business.slot_duration_min  = int(request.form.get('slot_duration_min', 30))
        except ValueError:
            pass

        # Logo (upload)
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            ext = logo_file.filename.rsplit('.', 1)[-1].lower()
            if ext in ('png', 'jpg', 'jpeg', 'svg', 'webp'):
                upload_dir = os.path.join(current_app.root_path, 'static', 'img', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f'logo_{business.id}.{ext}'
                logo_file.save(os.path.join(upload_dir, filename))
                business.logo_url = url_for('static', filename=f'img/uploads/{filename}')
            else:
                flash('Formato de imagen no soportado. Usa PNG, JPG o SVG.', 'error')

        db.session.commit()
        flash('¡Cambios guardados correctamente!', 'success')
        return redirect(url_for('dashboard.customize'))

    google_fonts = ['Syne', 'Outfit', 'Plus Jakarta Sans', 'DM Sans',
                    'Montserrat', 'Raleway', 'Poppins', 'Nunito', 'Space Grotesk']
    return render_template('dashboard/customize.html',
                           business=business,
                           google_fonts=google_fonts)


@dashboard_bp.route('/dashboard/services', methods=['GET', 'POST'])
@login_required
@require_active_subscription
def services():
    business = current_user.business

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name', '').strip()
            if name:
                svc = Service(
                    business_id=business.id,
                    name=name,
                    emoji=request.form.get('emoji', '⚡'),
                    description=request.form.get('description', '').strip(),
                    duration_min=int(request.form.get('duration_min', 30)),
                    price=int(request.form.get('price', 0)),
                )
                db.session.add(svc)
                db.session.commit()
                flash(f'Servicio "{name}" agregado', 'success')

        elif action == 'delete':
            svc_id = request.form.get('service_id')
            svc = Service.query.filter_by(id=svc_id, business_id=business.id).first()
            if svc:
                db.session.delete(svc)
                db.session.commit()
                flash('Servicio eliminado', 'success')

        elif action == 'toggle':
            svc_id = request.form.get('service_id')
            svc = Service.query.filter_by(id=svc_id, business_id=business.id).first()
            if svc:
                svc.is_active = not svc.is_active
                db.session.commit()

        return redirect(url_for('dashboard.services'))

    svcs = business.services.order_by(Service.order, Service.id).all()
    return render_template('dashboard/services.html', business=business, services=svcs)


@dashboard_bp.route('/dashboard/appointments')
@login_required
def appointments():
    business = current_user.business
    status_filter = request.args.get('status', 'all')
    date_filter   = request.args.get('date', '')

    query = business.appointments

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Appointment.date == filter_date)
        except ValueError:
            pass

    appts = query.order_by(Appointment.date.desc(), Appointment.time).all()
    return render_template('dashboard/appointments.html',
                           business=business,
                           appointments=appts,
                           status_filter=status_filter,
                           date_filter=date_filter)


@dashboard_bp.route('/dashboard/appointments/<int:appt_id>/status', methods=['POST'])
@login_required
def update_appointment_status(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.business.owner_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403

    new_status = request.json.get('status')
    if new_status in ('pending', 'confirmed', 'cancelled', 'completed'):
        appt.status = new_status
        db.session.commit()
        return jsonify({'ok': True, 'status': new_status})
    return jsonify({'error': 'Estado inválido'}), 400


@dashboard_bp.route('/dashboard/hours', methods=['GET', 'POST'])
@login_required
@require_active_subscription
def hours():
    business = current_user.business

    if request.method == 'POST':
        for day in range(7):
            wh = WorkingHours.query.filter_by(
                business_id=business.id, day_of_week=day).first()
            if not wh:
                wh = WorkingHours(business_id=business.id, day_of_week=day)
                db.session.add(wh)

            is_closed = request.form.get(f'closed_{day}') == 'on'
            wh.is_closed = is_closed
            if not is_closed:
                try:
                    open_str  = request.form.get(f'open_{day}', '09:00')
                    close_str = request.form.get(f'close_{day}', '18:00')
                    wh.open_time  = datetime.strptime(open_str,  '%H:%M').time()
                    wh.close_time = datetime.strptime(close_str, '%H:%M').time()
                except ValueError:
                    pass

        db.session.commit()
        flash('Horarios actualizados', 'success')
        return redirect(url_for('dashboard.hours'))

    wh_list = WorkingHours.query.filter_by(business_id=business.id).order_by(
        WorkingHours.day_of_week).all()
    wh_dict = {wh.day_of_week: wh for wh in wh_list}
    return render_template('dashboard/hours.html', business=business, wh_dict=wh_dict)


@dashboard_bp.route('/dashboard/staff', methods=['GET', 'POST'])
@login_required
@require_active_subscription
def staff():
    from models import Staff
    business = current_user.business

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name', '').strip()
            if name:
                s = Staff(business_id=business.id,
                          name=name,
                          role=request.form.get('role', '').strip(),
                          bio=request.form.get('bio', '').strip(),
                          instagram=request.form.get('instagram', '').strip().lstrip('@'),
                          email=request.form.get('staff_email', '').strip(),
                          phone=request.form.get('phone', '').strip())
                db.session.add(s)
                db.session.flush()
                # avatar upload
                avatar = request.files.get('avatar')
                if avatar and avatar.filename:
                    import os
                    ext = avatar.filename.rsplit('.', 1)[-1].lower()
                    if ext in ('png','jpg','jpeg','webp'):
                        upload_dir = os.path.join(current_app.root_path, 'static', 'img', 'uploads')
                        os.makedirs(upload_dir, exist_ok=True)
                        fname = f'staff_{s.id}.{ext}'
                        avatar.save(os.path.join(upload_dir, fname))
                        s.avatar_url = url_for('static', filename=f'img/uploads/{fname}')
                db.session.commit()
                flash(f'Colaborador "{name}" agregado', 'success')
        elif action == 'toggle':
            sid = request.form.get('staff_id')
            s = Staff.query.filter_by(id=sid, business_id=business.id).first()
            if s:
                s.is_active = not s.is_active
                db.session.commit()
        elif action == 'delete':
            sid = request.form.get('staff_id')
            s = Staff.query.filter_by(id=sid, business_id=business.id).first()
            if s:
                db.session.delete(s)
                db.session.commit()
                flash('Colaborador eliminado', 'success')
        return redirect(url_for('dashboard.staff'))

    from models import Staff
    staff_list = Staff.query.filter_by(business_id=business.id).all()
    return render_template('dashboard/staff.html', business=business, staff_list=staff_list)


@dashboard_bp.route('/dashboard/email', methods=['GET', 'POST'])
@login_required
@require_active_subscription
def email_settings():
    business = current_user.business

    if request.method == 'POST':
        business.email_subject    = request.form.get('email_subject', '').strip()
        business.email_greeting   = request.form.get('email_greeting', '').strip()
        business.email_footer_msg = request.form.get('email_footer_msg', '').strip()
        business.email_accent_color = request.form.get('email_accent_color', '#000000')
        business.email_bg_color     = request.form.get('email_bg_color', '#ffffff')
        business.send_confirmation  = request.form.get('send_confirmation') == 'on'
        db.session.commit()
        flash('Configuración de email guardada', 'success')
        return redirect(url_for('dashboard.email_settings'))

    return render_template('dashboard/email_settings.html', business=business)
