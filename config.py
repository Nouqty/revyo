import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MP_ACCESS_TOKEN = os.environ.get('MP_ACCESS_TOKEN', '')
    MP_PUBLIC_KEY = os.environ.get('MP_PUBLIC_KEY', '')
    MP_WEBHOOK_SECRET = os.environ.get('MP_WEBHOOK_SECRET', '')
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
    PLAN_BASIC_PRICE = int(os.environ.get('PLAN_BASIC_PRICE', 9900))
    PLAN_PRO_PRICE = int(os.environ.get('PLAN_PRO_PRICE', 19900))
    PLAN_CURRENCY = os.environ.get('PLAN_CURRENCY', 'CLP')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = 'static/img/uploads'
    MAIL_SERVER         = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT           = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS        = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME       = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@revyo.app')
    RESEND_API_KEY      = os.environ.get('RESEND_API_KEY', '')
    BREVO_API_KEY       = os.environ.get('BREVO_API_KEY', '')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig
}