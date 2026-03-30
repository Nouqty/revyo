from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from models import db, Owner, Business, Subscription, WorkingHours
import re

auth_bp = Blueprint('auth', __name__)

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


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        email        = request.form.get('email', '').strip().lower()
        password     = request.form.get('password', '')
        password2    = request.form.get('password2', '')
        business_name = request.form.get('business_name', '').strip()
        category     = request.form.get('category', 'general')

        # Validaciones
        errors = []
        if not name:           errors.append('El nombre es requerido')
        if not email:          errors.append('El email es requerido')
        if len(password) < 6:  errors.append('La contraseña debe tener al menos 6 caracteres')
        if password != password2: errors.append('Las contraseñas no coinciden')
        if not business_name:  errors.append('El nombre del negocio es requerido')

        if Owner.query.filter_by(email=email).first():
            errors.append('Ya existe una cuenta con ese email')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('auth/register.html',
                                   name=name, email=email,
                                   business_name=business_name, category=category)

        # Crear owner
        owner = Owner(name=name, email=email)
        owner.set_password(password)
        db.session.add(owner)
        db.session.flush()  # get owner.id

        # Crear suscripción trial (7 días)
        sub = Subscription(
            owner_id=owner.id,
            plan='basic',
            status='trial',
            trial_ends_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(sub)

        # Crear negocio
        base_slug = slugify(business_name)
        slug = base_slug
        counter = 1
        while Business.query.filter_by(slug=slug).first():
            slug = f'{base_slug}-{counter}'
            counter += 1

        business = Business(
            owner_id=owner.id,
            name=business_name,
            slug=slug,
            category=category
        )
        db.session.add(business)
        db.session.flush()

        # Crear horarios por defecto (Lun-Vie 9:00-18:00, Sáb 10:00-14:00, Dom cerrado)
        from datetime import time
        default_hours = [
            (0, time(9, 0), time(18, 0), False),   # Lunes
            (1, time(9, 0), time(18, 0), False),   # Martes
            (2, time(9, 0), time(18, 0), False),   # Miércoles
            (3, time(9, 0), time(18, 0), False),   # Jueves
            (4, time(9, 0), time(18, 0), False),   # Viernes
            (5, time(10, 0), time(14, 0), False),  # Sábado
            (6, None, None, True),                  # Domingo (cerrado)
        ]
        for day, open_t, close_t, closed in default_hours:
            wh = WorkingHours(
                business_id=business.id,
                day_of_week=day,
                open_time=open_t,
                close_time=close_t,
                is_closed=closed
            )
            db.session.add(wh)

        db.session.commit()

        login_user(owner)
        flash(f'¡Bienvenido {name}! Tu período de prueba de 7 días ha comenzado.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        owner = Owner.query.filter_by(email=email).first()
        if owner and owner.check_password(password):
            login_user(owner, remember=bool(remember))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Email o contraseña incorrectos', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('main.landing'))
