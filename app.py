import os
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from models import db, Owner
from config import config
from routes import main_bp, auth_bp, dashboard_bp, booking_bp, payment_bp

mail = Mail()

def create_app(config_name=None):
    app = Flask(__name__)
    env = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config.get(env, config['default']))

    db.init_app(app)
    mail.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view    = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para continuar'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return Owner.query.get(int(user_id))

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(payment_bp)

    with app.app_context():
        db.create_all()

    # Iniciar scheduler de recordatorios (solo en producción o si hay email config)
    if app.config.get('MAIL_USERNAME'):
        try:
            from scheduler import init_scheduler
            init_scheduler(app)
        except Exception as e:
            app.logger.warning(f'Scheduler no iniciado: {e}')

    @app.template_filter('format_time')
    def format_time(t):
        return t.strftime('%H:%M') if t else ''

    @app.template_filter('format_date')
    def format_date(d):
        if not d: return ''
        MONTHS = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        return f'{d.day} {MONTHS[d.month-1]} {d.year}'

    @app.template_filter('price_display')
    def price_display(p):
        return 'Gratis' if p == 0 else f'${p:,}'

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
