from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db, Subscription
import mercadopago
import json

payment_bp = Blueprint('payment', __name__)


def get_mp_sdk():
    return mercadopago.SDK(current_app.config['MP_ACCESS_TOKEN'])


@payment_bp.route('/planes')
def plans():
    sub = None
    if current_user.is_authenticated:
        sub = current_user.subscription
    return render_template('payment/plans.html', sub=sub)


@payment_bp.route('/suscribir/<plan>', methods=['POST'])
@login_required
def subscribe(plan):
    if plan not in ('basic', 'pro'):
        flash('Plan inválido', 'error')
        return redirect(url_for('payment.plans'))

    price = (current_app.config['PLAN_BASIC_PRICE']
             if plan == 'basic'
             else current_app.config['PLAN_PRO_PRICE'])

    sdk = get_mp_sdk()

    # Crear preferencia de pago (checkout pro)
    preference_data = {
        "items": [{
            "id": f"plan_{plan}",
            "title": f"Revyo — Plan {plan.capitalize()} (mensual)",
            "quantity": 1,
            "currency_id": current_app.config['PLAN_CURRENCY'],
            "unit_price": price / 100 if current_app.config['PLAN_CURRENCY'] in ('USD', 'EUR') else price,
        }],
        "payer": {
            "email": current_user.email,
            "name": current_user.name,
        },
        "back_urls": {
            "success": url_for('payment.success', _external=True) + f'?plan={plan}',
            "failure": url_for('payment.failure', _external=True),
            "pending": url_for('payment.pending', _external=True),
        },
        "auto_return": "approved",
        "metadata": {
            "owner_id": str(current_user.id),
            "plan": plan,
        },
        "notification_url": url_for('payment.webhook', _external=True),
        "statement_descriptor": "REVYO",
    }

    result = sdk.preference().create(preference_data)

    if result["status"] == 201:
        init_point = result["response"]["init_point"]
        return redirect(init_point)
    else:
        flash('Error al crear el pago. Intenta nuevamente.', 'error')
        return redirect(url_for('payment.plans'))


@payment_bp.route('/pago/exito')
@login_required
def success():
    plan           = request.args.get('plan', 'basic')
    payment_id     = request.args.get('payment_id')
    status         = request.args.get('status')
    preference_id  = request.args.get('preference_id')

    if status == 'approved':
        sub = current_user.subscription
        if not sub:
            sub = Subscription(owner_id=current_user.id)
            db.session.add(sub)

        sub.plan           = plan
        sub.status         = 'active'
        sub.mp_sub_id      = payment_id
        sub.mp_payer_email = current_user.email
        sub.next_payment_at = datetime.utcnow() + timedelta(days=30)
        db.session.commit()

        flash(f'¡Suscripción activada! Bienvenido al plan {plan.capitalize()}.', 'success')
    else:
        flash('El pago está en proceso. Te notificaremos cuando se confirme.', 'info')

    return redirect(url_for('dashboard.index'))


@payment_bp.route('/pago/fallo')
def failure():
    flash('El pago no pudo completarse. Puedes intentarlo nuevamente.', 'error')
    return redirect(url_for('payment.plans'))


@payment_bp.route('/pago/pendiente')
def pending():
    flash('Tu pago está pendiente de acreditación. Te notificaremos por email.', 'info')
    return redirect(url_for('dashboard.index'))


@payment_bp.route('/webhook/mercadopago', methods=['POST'])
def webhook():
    """IPN / Webhook de MercadoPago para notificaciones de pago."""
    data = request.json or {}
    topic = data.get('type') or request.args.get('topic', '')

    # Solo procesar pagos y suscripciones
    if topic in ('payment', 'preapproval'):
        resource_id = data.get('data', {}).get('id') or request.args.get('id')
        if resource_id:
            sdk = get_mp_sdk()

            if topic == 'payment':
                result = sdk.payment().get(resource_id)
                if result['status'] == 200:
                    payment = result['response']
                    metadata = payment.get('metadata', {})
                    owner_id = metadata.get('owner_id')
                    plan     = metadata.get('plan', 'basic')

                    if owner_id and payment.get('status') == 'approved':
                        sub = Subscription.query.filter_by(owner_id=owner_id).first()
                        if sub:
                            sub.status        = 'active'
                            sub.plan          = plan
                            sub.mp_sub_id     = str(resource_id)
                            sub.next_payment_at = datetime.utcnow() + timedelta(days=30)
                            db.session.commit()

    return jsonify({'status': 'ok'}), 200


@payment_bp.route('/cancelar-suscripcion', methods=['POST'])
@login_required
def cancel():
    sub = current_user.subscription
    if sub:
        sub.status = 'cancelled'
        db.session.commit()
        flash('Suscripción cancelada. Puedes seguir usando la app hasta el fin del período.', 'info')
    return redirect(url_for('payment.plans'))
