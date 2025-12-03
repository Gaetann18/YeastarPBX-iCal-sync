from flask import Blueprint, jsonify, request
from app.models import db, Extension, Schedule, Log, Config, Override
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/extensions', methods=['GET'])
def list_extensions():
    extensions = Extension.query.order_by(Extension.number).all()

    data = []
    for ext in extensions:
        data.append({
            'id': ext.id,
            'yeastar_id': ext.yeastar_id,
            'number': ext.number,
            'name': ext.name,
            'email': ext.email,
            'current_status': ext.current_status,
            'planning_enabled': ext.planning_enabled,
            'last_synced_at': ext.last_synced_at.isoformat() if ext.last_synced_at else None
        })

    return jsonify({'success': True, 'data': data})


@api_bp.route('/extensions/<int:extension_id>', methods=['GET'])
def get_extension(extension_id):
    extension = Extension.query.get_or_404(extension_id)

    schedules = Schedule.query.filter_by(extension_id=extension_id).all()
    schedules_data = [{
        'id': s.id,
        'day_of_week': s.day_of_week,
        'start_time': s.start_time,
        'end_time': s.end_time,
        'status': s.status
    } for s in schedules]

    overrides = Override.query.filter_by(extension_id=extension_id).all()
    overrides_data = [{
        'id': o.id,
        'status': o.status,
        'reason': o.reason,
        'expires_at': o.expires_at.isoformat() if o.expires_at else None,
        'created_at': o.created_at.isoformat()
    } for o in overrides]

    return jsonify({
        'success': True,
        'data': {
            'id': extension.id,
            'number': extension.number,
            'name': extension.name,
            'current_status': extension.current_status,
            'planning_enabled': extension.planning_enabled,
            'schedules': schedules_data,
            'overrides': overrides_data
        }
    })


@api_bp.route('/logs', methods=['GET'])
def get_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    extension_id = request.args.get('extension_id', type=int)

    query = Log.query

    if extension_id:
        query = query.filter_by(extension_id=extension_id)

    logs = query.order_by(Log.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    data = []
    for log in logs.items:
        data.append({
            'id': log.id,
            'extension_id': log.extension_id,
            'extension_number': log.extension.number if log.extension else None,
            'action': log.action,
            'old_status': log.old_status,
            'new_status': log.new_status,
            'trigger_type': log.trigger_type,
            'details': log.details,
            'created_at': log.created_at.isoformat()
        })

    return jsonify({
        'success': True,
        'data': data,
        'pagination': {
            'page': logs.page,
            'per_page': logs.per_page,
            'total': logs.total,
            'pages': logs.pages
        }
    })


@api_bp.route('/stats', methods=['GET'])
def get_stats():
    total_extensions = Extension.query.count()
    planning_enabled = Extension.query.filter_by(planning_enabled=True).count()

    status_counts = {}
    for ext in Extension.query.all():
        status = ext.current_status or 'unknown'
        status_counts[status] = status_counts.get(status, 0) + 1

    config = Config.query.first()

    return jsonify({
        'success': True,
        'data': {
            'total_extensions': total_extensions,
            'planning_enabled': planning_enabled,
            'status_counts': status_counts,
            'sync_interval_minutes': config.sync_interval_minutes if config else None
        }
    })
