from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging

scheduler = BackgroundScheduler()

def send_reminders(app):
    """Corre cada 15 minutos — envía recordatorios a citas que son en ~1 hora"""
    with app.app_context():
        from models import db, Appointment
        from flask_mail import Message
        from app import mail

        now = datetime.now()
        window_start = now + timedelta(minutes=55)
        window_end   = now + timedelta(minutes=75)

        appts = Appointment.query.filter(
            Appointment.status.in_(['pending', 'confirmed']),
            Appointment.customer_email != None,
            Appointment.customer_email != ''
        ).all()

        for appt in appts:
            if not appt.date or not appt.time:
                continue
            appt_dt = datetime.combine(appt.date, appt.time)
            if not (window_start <= appt_dt <= window_end):
                continue

            business = appt.business
            try:
                html = f"""
                <div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:20px">
                  <div style="background:{business.email_accent_color or '#000'};padding:24px;border-radius:12px 12px 0 0;text-align:center">
                    <h2 style="color:#fff;margin:0;font-size:18px">{business.name}</h2>
                  </div>
                  <div style="background:#fff;padding:24px;border-radius:0 0 12px 12px;border:1px solid #e5e7eb;border-top:none">
                    <p style="font-size:16px;font-weight:700;margin:0 0 8px">⏰ Recordatorio de tu cita</p>
                    <p style="color:#4b5563;margin:0 0 16px">Hola <strong>{appt.customer_name}</strong>, tu cita es en aproximadamente 1 hora.</p>
                    <div style="background:#f8f9fa;border-radius:8px;padding:14px;margin-bottom:16px">
                      {'<p style=\"margin:4px 0;font-size:14px\"><strong>Servicio:</strong> ' + appt.service.name + '</p>' if appt.service else ''}
                      <p style="margin:4px 0;font-size:14px"><strong>Hora:</strong> {appt.time.strftime('%H:%M')}</p>
                      {'<p style=\"margin:4px 0;font-size:14px\"><strong>Dirección:</strong> ' + business.address + '</p>' if business.address else ''}
                    </div>
                    <p style="color:#6b7280;font-size:13px">¡Te esperamos!</p>
                    <hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">
                    <p style="font-size:11px;color:#9ca3af;text-align:center">Revyo · Made by Nouqty</p>
                  </div>
                </div>"""

                msg = Message(
                    subject=f'⏰ Recordatorio: tu cita en {business.name} es en 1 hora',
                    recipients=[appt.customer_email],
                    html=html,
                    sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@revyo.app')
                )
                mail.send(msg)
                logging.info(f'Recordatorio enviado a {appt.customer_email}')
            except Exception as e:
                logging.warning(f'Error enviando recordatorio: {e}')

        # Notificar al colaborador si tiene email
        for appt in appts:
            if not appt.staff or not appt.staff.email:
                continue
            appt_dt = datetime.combine(appt.date, appt.time)
            if not (window_start <= appt_dt <= window_end):
                continue
            business = appt.business
            try:
                html = f"""
                <div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:20px">
                  <p style="font-size:15px">Hola <strong>{appt.staff.name}</strong>, tienes una cita en 1 hora:</p>
                  <div style="background:#f8f9fa;border-radius:8px;padding:14px">
                    <p style="margin:4px 0"><strong>Cliente:</strong> {appt.customer_name}</p>
                    {'<p style="margin:4px 0"><strong>Tel:</strong> ' + appt.customer_phone + '</p>' if appt.customer_phone else ''}
                    {'<p style="margin:4px 0"><strong>Servicio:</strong> ' + appt.service.name + '</p>' if appt.service else ''}
                    <p style="margin:4px 0"><strong>Hora:</strong> {appt.time.strftime('%H:%M')}</p>
                  </div>
                </div>"""
                msg = Message(
                    subject=f'Tienes una cita en 1 hora — {appt.customer_name}',
                    recipients=[appt.staff.email],
                    html=html,
                    sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@revyo.app')
                )
                mail.send(msg)
            except Exception as e:
                logging.warning(f'Error notif colaborador: {e}')

def init_scheduler(app):
    scheduler.add_job(
        func=send_reminders,
        args=[app],
        trigger='interval',
        minutes=15,
        id='send_reminders',
        replace_existing=True
    )
    scheduler.start()
