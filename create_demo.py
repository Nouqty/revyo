"""
Corre este script UNA VEZ en producción para crear el negocio demo.
python create_demo.py
"""
from app import app
from models import db, Owner, Business, Service, Staff, WorkingHours, Subscription
from datetime import datetime, timedelta, time
import re

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

with app.app_context():
    # Verificar si ya existe
    existing = Business.query.filter_by(slug='barberia-nova').first()
    if existing:
        print('Demo ya existe en slug: barberia-nova')
        exit()

    # Crear owner demo
    owner = Owner(name='Demo Revyo', email='demo@revyo.app')
    owner.set_password('demo12345')
    db.session.add(owner)
    db.session.flush()

    # Suscripción activa
    sub = Subscription(
        owner_id=owner.id, plan='basic', status='active',
        next_payment_at=datetime.utcnow() + timedelta(days=365)
    )
    db.session.add(sub)

    # Negocio demo
    biz = Business(
        owner_id=owner.id,
        name='Barbería Nova',
        slug='barberia-nova',
        description='La mejor barbería de la ciudad. Cortes modernos, barba perfecta y atención de calidad.',
        category='barberia',
        phone='+56 9 9999 8888',
        address='Av. Principal 123, Santiago',
        instagram='@barberia.nova',
        whatsapp='+56999998888',
        primary_color='#0a0a0f',
        secondary_color='#111118',
        accent_color='#7c3aed',
        text_color='#ffffff',
        font_choice='Syne',
        button_style='pill',
        card_style='elevated',
        header_style='gradient',
        allow_dark_mode=True,
        dark_bg_color='#08080f',
        dark_card_color='#111118',
        slot_duration_min=30,
        booking_lead_hours=1,
        max_advance_days=30,
        send_confirmation=True,
        email_subject='Tu reserva en Barbería Nova ✓',
        email_greeting='Hola {nombre}, gracias por reservar con nosotros. Tu cita ha sido registrada.',
        email_footer_msg='Para cualquier consulta escríbenos por WhatsApp.',
        email_accent_color='#7c3aed',
        email_bg_color='#f5f5f8',
    )
    db.session.add(biz)
    db.session.flush()

    # Servicios
    services = [
        ('✂', 'Corte Clásico', 'Corte preciso con tijera y máquina', 30, 8000),
        ('💈', 'Corte + Barba', 'Corte completo más perfilado de barba', 45, 12000),
        ('🪒', 'Afeitado Clásico', 'Afeitado con navaja y toalla caliente', 30, 9000),
        ('✨', 'Degradado', 'Degradado moderno con acabado premium', 40, 10000),
        ('💆', 'Tratamiento capilar', 'Hidratación profunda y masaje de cuero cabelludo', 45, 15000),
    ]
    for i, (emoji, name, desc, duration, price) in enumerate(services):
        svc = Service(business_id=biz.id, emoji=emoji, name=name,
                      description=desc, duration_min=duration, price=price,
                      is_active=True, order=i)
        db.session.add(svc)

    # Staff
    staff_data = [
        ('Carlos Mendoza', 'Barbero Senior', '8 años de experiencia. Especialista en degradados y cortes modernos.', '@carlosmendoza'),
        ('Diego Rojas', 'Estilista', 'Experto en tratamientos capilares y estilos clásicos.', '@diegorojas'),
    ]
    for name, role, bio, ig in staff_data:
        s = Staff(business_id=biz.id, name=name, role=role, bio=bio,
                  instagram=ig.replace('@',''), is_active=True)
        db.session.add(s)

    # Horarios
    hours = [
        (0, time(9,0), time(19,0), False),
        (1, time(9,0), time(19,0), False),
        (2, time(9,0), time(19,0), False),
        (3, time(9,0), time(19,0), False),
        (4, time(9,0), time(19,0), False),
        (5, time(10,0), time(17,0), False),
        (6, None, None, True),
    ]
    for day, open_t, close_t, closed in hours:
        wh = WorkingHours(business_id=biz.id, day_of_week=day,
                          open_time=open_t, close_time=close_t, is_closed=closed)
        db.session.add(wh)

    db.session.commit()
    print('Demo creado exitosamente!')
    print('URL: /b/barberia-nova')
    print('Login demo: demo@revyo.app / demo12345')
