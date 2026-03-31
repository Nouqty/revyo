import resend
import logging
from flask import current_app, render_template, url_for


def send_email(to, subject, html):
    """Envía email via Resend."""
    api_key = current_app.config.get('RESEND_API_KEY', '')
    if not api_key:
        logging.warning('RESEND_API_KEY no configurado')
        return False
    try:
        resend.api_key = api_key
        sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'Revyo <onboarding@resend.dev>')
        # Resend requiere formato "Nombre <email>"
        if '@' in sender and '<' not in sender:
            sender = f'Revyo <{sender}>'
        resend.Emails.send({
            'from': sender,
            'to': [to],
            'subject': subject,
            'html': html,
        })
        logging.info(f'Email enviado a {to}')
        return True
    except Exception as e:
        logging.warning(f'Error Resend: {e}')
        return False


def send_confirmation_email(appt, business):
    """Email de confirmación al cliente."""
    if not business.send_confirmation or not appt.customer_email:
        return
    import threading
    t = threading.Thread(
        target=_send_confirmation_async,
        args=(current_app._get_current_object(), appt.id, business.id)
    )
    t.daemon = True
    t.start()


def _send_confirmation_async(app, appt_id, business_id):
    with app.app_context():
        from models import Appointment, Business
        from itsdangerous import URLSafeTimedSerializer
        appt = Appointment.query.get(appt_id)
        business = Business.query.get(business_id)
        if not appt or not business:
            return

        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        token = s.dumps({'appt_id': appt_id}, salt='cancel-appt')
        cancel_url = f"{app.config.get('APP_URL', '')}/cancelar/{token}"

        greeting = (business.email_greeting or '').replace('{nombre}', appt.customer_name)
        accent = business.email_accent_color or '#000000'
        r, g, b = int(accent[1:3],16), int(accent[3:5],16), int(accent[5:7],16)
        header_text = '#ffffff' if (0.299*r+0.587*g+0.114*b)/255 < 0.5 else '#000000'

        html = render_template('email/confirmation.html',
            subject=business.email_subject or 'Tu reserva ha sido recibida',
            biz_name=business.name,
            logo_url=(app.config.get('APP_URL','') + business.logo_url) if business.logo_url else None,
            biz_address=business.address or '',
            greeting=greeting,
            footer_msg=business.email_footer_msg or '',
            service_name=appt.service.name if appt.service else '',
            appt_date=appt.date.strftime('%d/%m/%Y') if appt.date else '',
            appt_time=appt.time.strftime('%H:%M') if appt.time else '',
            cancel_url=cancel_url,
            accent=accent,
            header_text=header_text,
            email_bg=business.email_bg_color or '#f0f2f5',
        )
        send_email(
            to=appt.customer_email,
            subject=business.email_subject or f'Reserva en {business.name} ✓',
            html=html
        )


def notify_staff(appt):
    """Email al colaborador cuando le hacen una reserva."""
    if not appt.staff or not appt.staff.email:
        return
    import threading
    t = threading.Thread(
        target=_notify_staff_async,
        args=(current_app._get_current_object(), appt.id)
    )
    t.daemon = True
    t.start()


def _notify_staff_async(app, appt_id):
    with app.app_context():
        from models import Appointment
        appt = Appointment.query.get(appt_id)
        if not appt:
            return
        hora = appt.time.strftime('%H:%M') if appt.time else ''
        html = (
            '<div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:20px">'
            '<div style="background:#111827;padding:20px;border-radius:12px 12px 0 0;text-align:center">'
            f'<h2 style="color:#fff;margin:0">Nueva reserva 📅</h2>'
            '</div>'
            '<div style="background:#fff;padding:24px;border-radius:0 0 12px 12px;border:1px solid #e5e7eb">'
            f'<p>Hola <b>{appt.staff.name}</b>, tienes una nueva cita:</p>'
            '<div style="background:#f8f9fa;border-radius:8px;padding:16px;margin:12px 0">'
            f'<p style="margin:6px 0"><b>👤 Cliente:</b> {appt.customer_name}</p>'
            f'<p style="margin:6px 0"><b>📱 Teléfono:</b> {appt.customer_phone or "No indicado"}</p>'
            f'<p style="margin:6px 0"><b>✉️ Email:</b> {appt.customer_email or "No indicado"}</p>'
            + (f'<p style="margin:6px 0"><b>⚡ Servicio:</b> {appt.service.name}</p>' if appt.service else '')
            + (f'<p style="margin:6px 0"><b>📅 Fecha:</b> {appt.date.strftime("%d/%m/%Y")}</p>' if appt.date else '')
            + f'<p style="margin:6px 0"><b>🕐 Hora:</b> {hora}</p>'
            + (f'<p style="margin:6px 0"><b>📝 Notas:</b> {appt.notes}</p>' if appt.notes else '')
            + '</div>'
            '<p style="color:#6b7280;font-size:13px">¡Que te vaya bien!</p>'
            '<hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">'
            '<p style="font-size:11px;color:#9ca3af;text-align:center">Revyo · Made by Nouqty</p>'
            '</div></div>'
        )
        send_email(
            to=appt.staff.email,
            subject=f'📅 Nueva cita — {appt.customer_name} a las {hora}',
            html=html
        )
