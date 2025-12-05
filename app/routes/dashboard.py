from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from app.models import db, Extension, Log, Config, Override
from app.services.scheduler import SchedulerService
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')


@dashboard_bp.route('/')
def index():
    extensions = Extension.query.order_by(Extension.number).all()
    config = Config.query.first()
    recent_logs = Log.query.order_by(Log.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
                           extensions=extensions,
                           config=config,
                           recent_logs=recent_logs)


@dashboard_bp.route('/refresh')
def refresh_extensions():
    success, message = SchedulerService.refresh_extensions_from_api()

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/sync')
def sync_now():
    try:
        SchedulerService.sync_all_extensions()
        flash('Synchronisation effectuée avec succès', 'success')
    except Exception as e:
        flash(f'Erreur lors de la synchronisation: {str(e)}', 'error')

    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/extension/<int:extension_id>/toggle-planning', methods=['POST'])
def toggle_planning(extension_id):
    extension = Extension.query.get_or_404(extension_id)
    extension.planning_enabled = not extension.planning_enabled
    db.session.commit()

    status = "activé" if extension.planning_enabled else "désactivé"
    flash(f'Planning {status} pour {extension.name}', 'success')

    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/extension/<int:extension_id>/toggle-override', methods=['POST'])
def toggle_override(extension_id):
    extension = Extension.query.get_or_404(extension_id)
    extension.override_enabled = not extension.override_enabled
    db.session.commit()

    status = "activé" if extension.override_enabled else "désactivé"
    flash(f'Override {status} pour {extension.name} - Le planning automatique sera {"ignoré" if extension.override_enabled else "appliqué"}',
          'success')

    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/extension/<int:extension_id>/override', methods=['POST'])
def set_override(extension_id):
    extension = Extension.query.get_or_404(extension_id)

    status = request.form.get('status')
    reason = request.form.get('reason', '')
    duration = request.form.get('duration', type=int)

    if not status:
        flash('Statut requis', 'error')
        return redirect(url_for('dashboard.index'))

    Override.query.filter_by(extension_id=extension_id).delete()

    expires_at = None
    if duration and duration > 0:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(hours=duration)

    override = Override(
        extension_id=extension_id,
        status=status,
        reason=reason,
        expires_at=expires_at
    )
    db.session.add(override)

    log = Log(
        extension_id=extension_id,
        action="Override manuel défini",
        new_status=status,
        trigger_type='override',
        details=f"Raison: {reason or 'Non spécifiée'}. Durée: {duration or 'Illimitée'} heures"
    )
    db.session.add(log)

    db.session.commit()

    flash(f'Override défini pour {extension.name}', 'success')
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/extension/<int:extension_id>/remove-override', methods=['POST'])
def remove_override(extension_id):
    Override.query.filter_by(extension_id=extension_id).delete()

    log = Log(
        extension_id=extension_id,
        action="Override supprimé",
        trigger_type='manual'
    )
    db.session.add(log)

    db.session.commit()

    flash('Override supprimé', 'success')
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/set-all-available', methods=['POST'])
def set_all_available():
    from app.services.yeastar_api import YeastarAPI, CryptoService

    config = Config.query.first()
    if not config:
        flash('Aucune configuration trouvée', 'error')
        return redirect(url_for('dashboard.index'))


    client_secret = CryptoService.decrypt(config.client_secret_encrypted)
    api = YeastarAPI(config.pbx_url, config.client_id, client_secret, config_model=config)

    extensions = Extension.query.all()
    success_count = 0
    error_count = 0

    for ext in extensions:
        success, message = api.update_extension_status(ext.yeastar_id, 'available')
        if success:
            ext.current_status = 'available'
            success_count += 1

            
            log = Log(
                extension_id=ext.id,
                action="Mise en disponible globale",
                old_status=ext.current_status,
                new_status='available',
                trigger_type='manual',
                details='Tous les utilisateurs mis en disponible'
            )
            db.session.add(log)
        else:
            error_count += 1

    db.session.commit()

    flash(f'{success_count} extensions mises en disponible, {error_count} erreurs', 'success' if error_count == 0 else 'warning')
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/api/extensions')
def api_extensions():
    extensions = Extension.query.order_by(Extension.number).all()

    data = []
    for ext in extensions:
        data.append({
            'id': ext.id,
            'number': ext.number,
            'name': ext.name,
            'status': ext.current_status,
            'planning_enabled': ext.planning_enabled,
            'last_synced': ext.last_synced_at.isoformat() if ext.last_synced_at else None
        })

    return jsonify(data)
