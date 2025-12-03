from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.models import db, Extension, Schedule
from app.services.planning_parser import PlanningParser
from app.services.ical_sync import ICalSyncService
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv

load_dotenv()

planning_bp = Blueprint('planning', __name__, url_prefix='/planning')


@planning_bp.route('/')
def index():
    extensions = Extension.query.filter_by(planning_enabled=True).order_by(Extension.number).all()
    planning_data = []
    for ext in extensions:
        schedules = Schedule.query.filter_by(extension_id=ext.id).order_by(Schedule.day_of_week, Schedule.start_time).all()
        planning_data.append({
            'extension': ext,
            'schedules': schedules
        })

    return render_template('planning.html', planning_data=planning_data)


@planning_bp.route('/import', methods=['POST'])
def import_planning():
    if 'file' not in request.files:
        flash('Aucun fichier fourni', 'error')
        return redirect(url_for('planning.index'))

    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('planning.index'))

    
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    if file_ext not in ['csv', 'json']:
        flash('Format de fichier non supporté. Utilisez CSV ou JSON', 'error')
        return redirect(url_for('planning.index'))

    try:
        content = file.read().decode('utf-8')
    except Exception as e:
        flash(f'Erreur de lecture du fichier: {str(e)}', 'error')
        return redirect(url_for('planning.index'))

  
    if file_ext == 'csv':
        schedules_data, message = PlanningParser.parse_csv(content)
    else:
        schedules_data, message = PlanningParser.parse_json(content)

    if schedules_data is None:
        flash(message, 'error')
        return redirect(url_for('planning.index'))

    
    imported_count = 0
    for schedule_data in schedules_data:
    
        extension = Extension.query.filter_by(number=schedule_data['extension']).first()

        if not extension:
            continue

        
        schedule = Schedule(
            extension_id=extension.id,
            day_of_week=schedule_data['day_of_week'],
            start_time=schedule_data['start_time'],
            end_time=schedule_data['end_time'],
            status=schedule_data['status']
        )
        db.session.add(schedule)
        imported_count += 1

    db.session.commit()
    flash(f'{imported_count} créneaux importés. {message}', 'success')
    return redirect(url_for('planning.index'))


@planning_bp.route('/extension/<int:extension_id>')
def view_extension(extension_id):
    from datetime import datetime, timedelta

    extension = Extension.query.get_or_404(extension_id)

    
    recurring_schedules = Schedule.query.filter_by(
        extension_id=extension_id,
        specific_date=None
    ).order_by(Schedule.day_of_week, Schedule.start_time).all()


    today = datetime.now().date()
    end_date = today + timedelta(days=30)

    specific_schedules = Schedule.query.filter(
        Schedule.extension_id == extension_id,
        Schedule.specific_date.isnot(None),
        Schedule.specific_date >= today,
        Schedule.specific_date <= end_date
    ).order_by(Schedule.specific_date, Schedule.start_time).all()

    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    weekly_schedule = {day: [] for day in days}

    for schedule in recurring_schedules:
        day_name = days[schedule.day_of_week]
        weekly_schedule[day_name].append(schedule)


    specific_by_date = {}
    for schedule in specific_schedules:
        date_str = schedule.specific_date.strftime('%Y-%m-%d')
        if date_str not in specific_by_date:
            specific_by_date[date_str] = []
        specific_by_date[date_str].append(schedule)

    return render_template('planning_detail.html',
                           extension=extension,
                           weekly_schedule=weekly_schedule,
                           days=days,
                           specific_by_date=specific_by_date,
                           has_recurring=len(recurring_schedules) > 0,
                           has_specific=len(specific_schedules) > 0)


@planning_bp.route('/extension/<int:extension_id>/add', methods=['POST'])
def add_schedule(extension_id):
    extension = Extension.query.get_or_404(extension_id)

    day_of_week = request.form.get('day_of_week', type=int)
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    status = request.form.get('status', 'available')

    if day_of_week is None or not start_time or not end_time:
        flash('Tous les champs sont requis', 'error')
        return redirect(url_for('planning.view_extension', extension_id=extension_id))


    if not PlanningParser.validate_time_format(start_time) or not PlanningParser.validate_time_format(end_time):
        flash('Format d\'heure invalide (HH:MM requis)', 'error')
        return redirect(url_for('planning.view_extension', extension_id=extension_id))
    schedule = Schedule(
        extension_id=extension_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        status=status
    )
    db.session.add(schedule)
    db.session.commit()

    flash('Créneau ajouté avec succès', 'success')
    return redirect(url_for('planning.view_extension', extension_id=extension_id))


@planning_bp.route('/schedule/<int:schedule_id>/delete', methods=['POST'])
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    extension_id = schedule.extension_id

    db.session.delete(schedule)
    db.session.commit()

    flash('Créneau supprimé', 'success')
    return redirect(url_for('planning.view_extension', extension_id=extension_id))


@planning_bp.route('/extension/<int:extension_id>/clear', methods=['POST'])
def clear_planning(extension_id):
    extension = Extension.query.get_or_404(extension_id)

    Schedule.query.filter_by(extension_id=extension_id).delete()
    db.session.commit()

    flash(f'Planning de {extension.name} effacé', 'success')
    return redirect(url_for('planning.index'))


@planning_bp.route('/extension/<int:extension_id>/sync-ical', methods=['POST'])
def sync_ical(extension_id):
    extension = Extension.query.get_or_404(extension_id)

    ical_token = request.form.get('ical_token', '').strip()

    if not ical_token:
        flash('Token iCal requis', 'error')
        return redirect(url_for('planning.view_extension', extension_id=extension_id))

    
    ical_base_url = os.getenv('ICAL_BASE_URL', 'https://cfamfeo.imfr.fr/V2/iplanning/feed/ical/?u=')
    ical_url = f"{ical_base_url}{ical_token}"

    
    ical_service = ICalSyncService()
    success = ical_service.sync_extension_from_ical(extension, ical_url)

    if success:
        
        extension.ical_token = ical_token
        db.session.commit()
        flash(f'Planning synchronisé depuis iPlanning pour {extension.name}', 'success')
    else:
        flash('Erreur lors de la synchronisation iCal. Vérifiez le token.', 'error')

    return redirect(url_for('planning.view_extension', extension_id=extension_id))


@planning_bp.route('/extension/<int:extension_id>/update-ical-token', methods=['POST'])
def update_ical_token(extension_id):
    extension = Extension.query.get_or_404(extension_id)

    ical_token = request.form.get('ical_token', '').strip()

    if ical_token:
        extension.ical_token = ical_token
        ical_base_url = os.getenv('ICAL_BASE_URL', 'https://cfamfeo.imfr.fr/V2/iplanning/feed/ical/?u=')
        extension.ical_url = f"{ical_base_url}{ical_token}"
        db.session.commit()
        flash(f'Token iCal mis à jour pour {extension.name}', 'success')
    else:
        flash('Token iCal vide', 'error')

    return redirect(url_for('planning.view_extension', extension_id=extension_id))


@planning_bp.route('/sync-all-ical', methods=['POST'])
def sync_all_ical():
    from app.services.ical_sync import ICalSyncService

    extensions = Extension.query.filter(Extension.ical_token.isnot(None)).all()

    if not extensions:
        flash('Aucune extension avec token iCal configuré', 'warning')
        return redirect(url_for('planning.index'))

    synced_count = 0
    error_count = 0

    ical_service = ICalSyncService()

    for extension in extensions:
        try:
            if extension.ical_url:
                success = ical_service.sync_extension_from_ical(extension, extension.ical_url)
                if success:
                    synced_count += 1
                else:
                    error_count += 1
        except Exception as e:
            error_count += 1

    if synced_count > 0:
        flash(f'✓ {synced_count} extensions synchronisées depuis iCal', 'success')
    if error_count > 0:
        flash(f'✗ {error_count} erreurs lors de la synchronisation', 'error')

    return redirect(url_for('planning.index'))
