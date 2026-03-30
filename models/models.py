from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ─────────────────────────────────────────────
# OWNER  (dueño del negocio / cliente del SaaS)
# ─────────────────────────────────────────────
class Owner(UserMixin, db.Model):
    __tablename__ = 'owners'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_active     = db.Column(db.Boolean, default=True)

    # Relationships
    subscription  = db.relationship('Subscription', backref='owner', uselist=False)
    business      = db.relationship('Business', backref='owner', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def has_active_subscription(self):
        if not self.subscription:
            return False
        return self.subscription.status in ('active', 'trial')

    def __repr__(self):
        return f'<Owner {self.email}>'


# ─────────────────────────────────────────────
# SUBSCRIPTION  (suscripción mensual via MercadoPago)
# ─────────────────────────────────────────────
class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id               = db.Column(db.Integer, primary_key=True)
    owner_id         = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)
    plan             = db.Column(db.String(20), default='basic')   # basic | pro
    status           = db.Column(db.String(20), default='trial')   # trial | active | paused | cancelled
    mp_sub_id        = db.Column(db.String(100))                   # ID de MercadoPago
    mp_payer_email   = db.Column(db.String(120))
    trial_ends_at    = db.Column(db.DateTime)
    next_payment_at  = db.Column(db.DateTime)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Subscription {self.plan} - {self.status}>'


# ─────────────────────────────────────────────
# BUSINESS  (el negocio / su página pública)
# ─────────────────────────────────────────────
class Business(db.Model):
    __tablename__ = 'businesses'
    id               = db.Column(db.Integer, primary_key=True)
    owner_id         = db.Column(db.Integer, db.ForeignKey('owners.id'), nullable=False)

    # Identidad
    name             = db.Column(db.String(120), nullable=False)
    slug             = db.Column(db.String(80), unique=True, nullable=False)   # URL: /b/mi-barberia
    description      = db.Column(db.Text)
    category         = db.Column(db.String(40), default='general')  # barberia|gym|spa|salon|otro

    # Contacto
    phone            = db.Column(db.String(20))
    address          = db.Column(db.String(200))
    instagram        = db.Column(db.String(80))
    whatsapp         = db.Column(db.String(20))

    # Personalización visual
    primary_color    = db.Column(db.String(7), default='#09090b')
    secondary_color  = db.Column(db.String(7), default='#18181b')
    accent_color     = db.Column(db.String(7), default='#fafafa')
    text_color       = db.Column(db.String(7), default='#ffffff')
    logo_url         = db.Column(db.String(300))
    banner_url       = db.Column(db.String(300))
    font_choice      = db.Column(db.String(40), default='Syne')

    # Nuevas opciones de diseño
    button_style     = db.Column(db.String(20), default='rounded')   # rounded | pill | square
    card_style       = db.Column(db.String(20), default='elevated')  # elevated | flat | bordered | glass
    header_style     = db.Column(db.String(20), default='gradient')  # gradient | solid | minimal | image
    allow_dark_mode  = db.Column(db.Boolean, default=True)           # mostrar toggle modo oscuro al cliente
    dark_bg_color    = db.Column(db.String(7), default='#0f0f1a')    # fondo en modo oscuro
    dark_card_color  = db.Column(db.String(7), default='#1a1a2e')    # cards en modo oscuro

    # Configuración de reservas
    booking_lead_hours   = db.Column(db.Integer, default=1)
    max_advance_days     = db.Column(db.Integer, default=30)
    slot_duration_min    = db.Column(db.Integer, default=30)
    is_active            = db.Column(db.Boolean, default=True)
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)

    # Email de confirmación
    email_subject      = db.Column(db.String(200), default='Tu reserva ha sido recibida ✓')
    email_greeting     = db.Column(db.Text, default='Hola {nombre}, gracias por reservar. Tu cita ha sido registrada correctamente.')
    email_footer_msg   = db.Column(db.Text, default='Si tienes alguna pregunta no dudes en contactarnos.')
    email_accent_color = db.Column(db.String(7), default='#000000')
    email_bg_color     = db.Column(db.String(7), default='#ffffff')
    send_confirmation  = db.Column(db.Boolean, default=True)

    # Relationships
    services     = db.relationship('Service',      backref='business', lazy='dynamic', cascade='all,delete')
    staff        = db.relationship('Staff',        backref='business', lazy='dynamic', cascade='all,delete')
    hours        = db.relationship('WorkingHours', backref='business', lazy='dynamic', cascade='all,delete')
    appointments = db.relationship('Appointment',  backref='business', lazy='dynamic', cascade='all,delete')

    def __repr__(self):
        return f'<Business {self.slug}>'


# ─────────────────────────────────────────────
# SERVICE  (servicios que ofrece el negocio)
# ─────────────────────────────────────────────
class Service(db.Model):
    __tablename__ = 'services'
    id              = db.Column(db.Integer, primary_key=True)
    business_id     = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    name            = db.Column(db.String(120), nullable=False)
    emoji           = db.Column(db.String(10), default='⚡')
    description     = db.Column(db.Text)
    duration_min    = db.Column(db.Integer, default=30)
    price           = db.Column(db.Integer, default=0)
    is_active       = db.Column(db.Boolean, default=True)
    order           = db.Column(db.Integer, default=0)

    def price_display(self):
        if self.price == 0:
            return 'Gratis'
        return f'${self.price:,}'

    def __repr__(self):
        return f'<Service {self.name}>'


# ─────────────────────────────────────────────
# STAFF  (profesionales del negocio, opcional)
# ─────────────────────────────────────────────
class Staff(db.Model):
    __tablename__ = 'staff'
    id          = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    name        = db.Column(db.String(120), nullable=False)
    role        = db.Column(db.String(80))
    bio         = db.Column(db.Text)
    avatar_url  = db.Column(db.String(300))
    instagram   = db.Column(db.String(100))
    email       = db.Column(db.String(120))
    phone       = db.Column(db.String(20))
    is_active   = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Staff {self.name}>'


# ─────────────────────────────────────────────
# WORKING HOURS  (horario de atención)
# ─────────────────────────────────────────────
class WorkingHours(db.Model):
    __tablename__ = 'working_hours'
    id          = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)   # 0=Lunes ... 6=Domingo
    open_time   = db.Column(db.Time)
    close_time  = db.Column(db.Time)
    is_closed   = db.Column(db.Boolean, default=False)

    DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

    @property
    def day_name(self):
        return self.DAY_NAMES[self.day_of_week]

    def __repr__(self):
        return f'<WorkingHours {self.day_name}>'


# ─────────────────────────────────────────────
# APPOINTMENT  (reserva / cita)
# ─────────────────────────────────────────────
class Appointment(db.Model):
    __tablename__ = 'appointments'
    id              = db.Column(db.Integer, primary_key=True)
    business_id     = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    service_id      = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    staff_id        = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)

    # Cliente
    customer_name   = db.Column(db.String(120), nullable=False)
    customer_email  = db.Column(db.String(120))
    customer_phone  = db.Column(db.String(20))

    # Cita
    date            = db.Column(db.Date, nullable=False)
    time            = db.Column(db.Time, nullable=False)
    duration_min    = db.Column(db.Integer, default=30)
    status          = db.Column(db.String(20), default='pending')  # pending|confirmed|cancelled|completed
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    service = db.relationship('Service', backref='appointments')
    staff   = db.relationship('Staff',   backref='appointments')

    STATUS_LABELS = {
        'pending':   ('Pendiente',  '#f59e0b'),
        'confirmed': ('Confirmada', '#10b981'),
        'cancelled': ('Cancelada',  '#ef4444'),
        'completed': ('Completada', '#6366f1'),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, ('Desconocido', '#9ca3af'))

    def __repr__(self):
        return f'<Appointment {self.customer_name} {self.date} {self.time}>'
