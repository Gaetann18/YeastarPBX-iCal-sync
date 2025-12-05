from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import os
import logging

from app.models import db


def create_app():
    instance_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    os.makedirs(os.path.join(instance_path, 'uploads'), exist_ok=True)

    app = Flask(__name__, instance_path=instance_path)

    app.config.from_object('app.config.Config')

    db.init_app(app)

    with app.app_context():
        db.create_all()

        from app.models import Config
        from app.services.yeastar_api import CryptoService

        config = Config.query.first()
        if not config:
            pbx_url = os.getenv('YEASTAR_PBX_URL')
            client_id = os.getenv('YEASTAR_CLIENT_ID')
            client_secret = os.getenv('YEASTAR_CLIENT_SECRET')
            sync_interval = int(os.getenv('SYNC_INTERVAL_MINUTES', 5))
            default_status = os.getenv('DEFAULT_STATUS', 'available')

            if pbx_url and client_id and client_secret:
                config = Config(
                    pbx_url=pbx_url,
                    client_id=client_id,
                    client_secret_encrypted=CryptoService.encrypt(client_secret),
                    sync_interval_minutes=sync_interval,
                    default_unavailable_status=default_status
                )
                db.session.add(config)
                db.session.commit()
                logging.info("Configuration initiale créée depuis .env")

    from datetime import datetime
    import pytz

    @app.template_filter('local_time')
    def local_time_filter(utc_dt):
        if utc_dt is None:
            return None
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        local_tz = pytz.timezone('Europe/Paris')
        return utc_dt.astimezone(local_tz)

    from app.status_mapping import get_status_display, get_status_label, get_status_badge_html

    @app.template_filter('status_label')
    def status_label_filter(status):
        return get_status_label(status)

    @app.template_filter('status_badge')
    def status_badge_filter(status):
        return get_status_badge_html(status)

    @app.context_processor
    def inject_status_mapping():
        return dict(get_status_display=get_status_display)
    from app.routes.dashboard import dashboard_bp
    from app.routes.planning import planning_bp
    from app.routes.api import api_bp
    from app.routes.config import config_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(planning_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(config_bp)

    scheduler = BackgroundScheduler()

    def sync_job():
        with app.app_context():
            from app.services.scheduler import SchedulerService
            from app.models import Config

            config = Config.query.first()
            if config:
                logging.info("Démarrage de la synchronisation automatique")
                SchedulerService.sync_all_extensions()

    def ical_sync_job():
        with app.app_context():
            from app.models import Extension
            from app.services.ical_sync import ICalSyncService
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Démarrage de la synchronisation iCal automatique")

            extensions = Extension.query.filter(Extension.ical_token.isnot(None)).all()

            synced_count = 0
            error_count = 0

            ical_service = ICalSyncService()

            for extension in extensions:
                try:
                    if extension.ical_url:
                        success = ical_service.sync_extension_from_ical(extension, extension.ical_url)
                        if success:
                            synced_count += 1
                            logger.info(f"✓ Extension {extension.number} synchronisée depuis iCal")
                        else:
                            error_count += 1
                            logger.warning(f"✗ Échec synchronisation iCal pour extension {extension.number}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"✗ Erreur synchronisation iCal pour extension {extension.number}: {e}")

            logger.info(f"Synchronisation iCal terminée: {synced_count} extensions synchronisées, {error_count} erreurs")

    with app.app_context():
        from app.models import Config
        config = Config.query.first()
        interval_minutes = config.sync_interval_minutes if config else 5

    scheduler.add_job(
        func=sync_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id='sync_extensions',
        name='Synchronisation des extensions',
        replace_existing=True
    )


    scheduler.add_job(
        func=ical_sync_job,
        trigger=IntervalTrigger(minutes=1),
        id='sync_ical',
        name='Synchronisation iCal',
        replace_existing=True
    )

    scheduler.start()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    return app
