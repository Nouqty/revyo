from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def landing():
    return render_template('landing.html')


@main_bp.route('/setup-demo-barberia-nova-revyo')
def setup_demo():
    """Ruta secreta para crear el negocio demo."""
    try:
        from models import db, Owner, Business, Service, Staff, WorkingHours, Subscription
        from datetime import datetime, timedelta, time
        import re

        existing = Business.query.filter_by(slug='barberia-nova').first()
        if existing:
            return '<h2>Demo ya existe. Ve a <a href="/b/barberia-nova">/b/barberia-nova</a></h2>'

        owner = Owner(name='Demo Revyo', email='demo@revyo.app')
        owner.set_password('demo12345')
        db.session.add(owner)
        db.session.flush()

        sub = Subscription(owner_id=owner.id, plan='basic', status='active',
                           next_payment_at=datetime.utcnow() + timedelta(days=365))
        db.session.add(sub)

        biz = Business(
            owner_id=owner.id, name='Barbería Nova', slug='barberia-nova',
            description='La mejor barbería de la ciudad. Cortes modernos y atención premium.',
            category='barberia', phone='+56 9 9999 8888',
            address='Av. Principal 123, Santiago', instagram='barberia.nova',
            whatsapp='+56999998888',
            primary_color='#0a0a0f', secondary_color='#111118',
            accent_color='#7c3aed', text_color='#ffffff',
            font_choice='Syne', button_style='pill', card_style='elevated',
            header_style='gradient', allow_dark_mode=True,
            dark_bg_color='#08080f', dark_card_color='#111118',
            slot_duration_min=30, booking_lead_hours=1, max_advance_days=30,
            send_confirmation=False,
        )
        db.session.add(biz)
        db.session.flush()

        for i, (emoji, name, desc, dur, price) in enumerate([
            ('✂', 'Corte Clásico', 'Corte preciso con tijera y máquina', 30, 8000),
            ('💈', 'Corte + Barba', 'Corte completo más perfilado de barba', 45, 12000),
            ('🪒', 'Afeitado Clásico', 'Afeitado con navaja y toalla caliente', 30, 9000),
            ('✨', 'Degradado Premium', 'Degradado moderno con acabado impecable', 40, 10000),
        ]):
            db.session.add(Service(business_id=biz.id, emoji=emoji, name=name,
                                   description=desc, duration_min=dur, price=price, order=i))

        for name, role, bio, ig in [
            ('Carlos Mendoza', 'Barbero Senior', '8 años de experiencia. Especialista en degradados.', 'carlosmendoza'),
            ('Diego Rojas', 'Estilista', 'Experto en cortes clásicos y tratamientos.', 'diegorojas'),
        ]:
            db.session.add(Staff(business_id=biz.id, name=name, role=role, bio=bio, instagram=ig, is_active=True))

        for day, open_t, close_t, closed in [
            (0, time(9,0), time(19,0), False), (1, time(9,0), time(19,0), False),
            (2, time(9,0), time(19,0), False), (3, time(9,0), time(19,0), False),
            (4, time(9,0), time(19,0), False), (5, time(10,0), time(17,0), False),
            (6, None, None, True),
        ]:
            db.session.add(WorkingHours(business_id=biz.id, day_of_week=day,
                                        open_time=open_t, close_time=close_t, is_closed=closed))

        db.session.commit()
        return '''<h2 style="font-family:sans-serif;padding:2rem">
            Demo creada exitosamente 🎉<br><br>
            <a href="/b/barberia-nova" style="color:#7c3aed">Ver Barbería Nova →</a>
        </h2>'''
    except Exception as e:
        return f'<h2 style="color:red">Error: {e}</h2>'
