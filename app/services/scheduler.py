from datetime import datetime, time
from app.models import db, Extension, Schedule, Override, Log, Config
from app.services.yeastar_api import YeastarAPI, CryptoService
import logging
import time as time_module

logger = logging.getLogger(__name__)


class SchedulerService:

    @staticmethod
    def get_current_day_of_week():
        return datetime.now().weekday()

    @staticmethod
    def get_current_time():
        return datetime.now().strftime('%H:%M')

    @staticmethod
    def time_in_range(start_str, end_str, current_str):
        start = datetime.strptime(start_str, '%H:%M').time()
        end = datetime.strptime(end_str, '%H:%M').time()
        current = datetime.strptime(current_str, '%H:%M').time()

        if start <= end:
            return start <= current <= end
        else:
            return current >= start or current <= end

    @staticmethod
    def get_desired_status(extension):
        active_override = Override.query.filter_by(extension_id=extension.id).filter(
            (Override.expires_at.is_(None)) | (Override.expires_at > datetime.utcnow())
        ).first()

        if active_override:
            return active_override.status, 'override'

        if not extension.planning_enabled:
            import os
            default_status = os.environ.get('DEFAULT_STATUS', 'available')
            return default_status, 'no_planning'

        if extension.override_enabled:
            logger.info(f"Extension {extension.number}: Override activé - planning automatique ignoré")
            return extension.current_status, 'override_manual'

        current_day = SchedulerService.get_current_day_of_week()
        current_time = SchedulerService.get_current_time()
        current_date = datetime.now().date()

        logger.debug(f"Extension {extension.number}: Recherche planning pour date={current_date}, heure={current_time}")

        specific_schedules = Schedule.query.filter_by(
            extension_id=extension.id,
            specific_date=current_date
        ).all()

        logger.debug(f"Extension {extension.number}: {len(specific_schedules)} plannings spécifiques trouvés pour aujourd'hui")

        for schedule in specific_schedules:
            logger.debug(f"Extension {extension.number}: Vérif créneau {schedule.start_time}-{schedule.end_time} (statut: {schedule.status})")
            if SchedulerService.time_in_range(schedule.start_time, schedule.end_time, current_time):
                logger.info(f"Extension {extension.number}: MATCH créneau spécifique {schedule.start_time}-{schedule.end_time} -> {schedule.status}")
                return schedule.status, 'schedule_specific'

        recurring_schedules = Schedule.query.filter_by(
            extension_id=extension.id,
            day_of_week=current_day,
            specific_date=None
        ).all()

        for schedule in recurring_schedules:
            if SchedulerService.time_in_range(schedule.start_time, schedule.end_time, current_time):
                return schedule.status, 'schedule_recurring'

        import os
        default_status = os.environ.get('DEFAULT_STATUS', 'available')
        return default_status, 'outside_schedule'

    @staticmethod
    def sync_all_extensions():
        import os

        pbx_url = os.environ.get('YEASTAR_PBX_URL')
        client_id = os.environ.get('YEASTAR_CLIENT_ID')
        client_secret = os.environ.get('YEASTAR_CLIENT_SECRET')

        if not pbx_url or not client_id or not client_secret:
            logger.error("Configuration API Yeastar manquante dans .env")
            return

        api = YeastarAPI(pbx_url, client_id, client_secret)

        extensions = Extension.query.filter_by(planning_enabled=True).all()
        logger.info(f"Synchronisation de {len(extensions)} extension(s) avec planning activé")

        synced_count = 0
        error_count = 0

        for extension in extensions:
            try:
                desired_status, reason = SchedulerService.get_desired_status(extension)

                if extension.current_status != desired_status:
                    time_module.sleep(0.5)
                    success, message = api.update_extension_status(extension.yeastar_id, desired_status)

                    if success:
                        old_status = extension.current_status
                        extension.current_status = desired_status
                        extension.last_synced_at = datetime.utcnow()

                        log = Log(
                            extension_id=extension.id,
                            action=f"Changement de statut automatique",
                            old_status=old_status,
                            new_status=desired_status,
                            trigger_type=reason,
                            details=f"Synchronisation automatique - {message}"
                        )
                        db.session.add(log)
                        synced_count += 1
                        logger.info(f"Extension {extension.number}: {old_status} -> {desired_status}")
                    else:
                        error_count += 1
                        logger.error(f"Erreur mise à jour extension {extension.number}: {message}")

                        log = Log(
                            extension_id=extension.id,
                            action="Échec de mise à jour",
                            trigger_type='api_error',
                            details=message
                        )
                        db.session.add(log)
                else:
                    extension.last_synced_at = datetime.utcnow()

            except Exception as e:
                error_count += 1
                logger.exception(f"Erreur lors de la synchronisation de l'extension {extension.number}")

                log = Log(
                    extension_id=extension.id,
                    action="Erreur de synchronisation",
                    trigger_type='api_error',
                    details=str(e)
                )
                db.session.add(log)

        db.session.commit()

        logger.info(f"Synchronisation terminée: {synced_count} mises à jour, {error_count} erreurs")

    @staticmethod
    def refresh_extensions_from_api():
        import os

        pbx_url = os.environ.get('YEASTAR_PBX_URL')
        client_id = os.environ.get('YEASTAR_CLIENT_ID')
        client_secret = os.environ.get('YEASTAR_CLIENT_SECRET')

        if not pbx_url or not client_id or not client_secret:
            return False, "Configuration API Yeastar manquante dans .env (YEASTAR_PBX_URL, YEASTAR_CLIENT_ID, YEASTAR_CLIENT_SECRET)"

        api = YeastarAPI(pbx_url, client_id, client_secret)

        extensions_data, message = api.get_extensions()
        if extensions_data is None:
            return False, message

        for i, ext_data in enumerate(extensions_data):
            if i > 0 and i % 10 == 0:
                time_module.sleep(1)

            extension = Extension.query.filter_by(yeastar_id=ext_data['id']).first()

            if extension:
                extension.number = ext_data['number']
                extension.name = ext_data.get('caller_id_name', '')
                extension.email = ext_data.get('email_addr', '')
                extension.current_status = ext_data.get('presence_status', 'unknown')
                extension.last_synced_at = datetime.utcnow()
            else:
                extension = Extension(
                    yeastar_id=ext_data['id'],
                    number=ext_data['number'],
                    name=ext_data.get('caller_id_name', ''),
                    email=ext_data.get('email_addr', ''),
                    current_status=ext_data.get('presence_status', 'unknown'),
                    last_synced_at=datetime.utcnow(),
                    planning_enabled=False
                )
                db.session.add(extension)

        db.session.commit()
        return True, f"{len(extensions_data)} extensions synchronisées"
