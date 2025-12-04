from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import db, Config
from app.services.yeastar_api import CryptoService

config_bp = Blueprint('config', __name__, url_prefix='/config')


@config_bp.route('/')
def index():
    config = Config.query.first()
    return render_template('config.html', config=config)


@config_bp.route('/update', methods=['POST'])
def update():
    config = Config.query.first()

    if not config:
        config = Config()
        db.session.add(config)

    config.pbx_url = request.form.get('pbx_url')
    config.client_id = request.form.get('client_id')

    # Only update client_secret if a new one is provided
    client_secret = request.form.get('client_secret')
    if client_secret:
        config.client_secret_encrypted = CryptoService.encrypt(client_secret)

    config.default_unavailable_status = request.form.get('default_unavailable_status', 'available')
    config.sync_interval_minutes = int(request.form.get('sync_interval_minutes', 5))

    db.session.commit()

    flash('Configuration mise à jour avec succès', 'success')
    return redirect(url_for('config.index'))
