import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ICalSyncService:
    """Service pour synchroniser les plannings depuis iCal/iPlanning"""

    def __init__(self, timezone='Europe/Paris'):
        self.timezone = pytz.timezone(timezone)

    def fetch_ical(self, url: str) -> Optional[Calendar]:
        """
        Récupère et parse un calendrier iCal depuis une URL

        Args:
            url: URL du flux iCal (ex: https://cfamfeo.imfr.fr/V2/iplanning/feed/ical/?u=TOKEN)

        Returns:
            Calendar object ou None si erreur
        """
        try:
            logger.info(f"Récupération du calendrier iCal depuis: {url}")
            response = requests.get(url, timeout=30, verify=False)
            response.raise_for_status()
            logger.info(f"Réponse HTTP {response.status_code}, taille: {len(response.content)} bytes")

            calendar = Calendar.from_ical(response.content)
            logger.info("Calendrier iCal parsé avec succès")
            return calendar
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du calendrier iCal: {e}")
            return None

    def parse_events(self, calendar: Calendar, days_ahead: int = 30) -> List[Dict]:
        """
        Parse les événements du calendrier et les convertit en créneaux de planning

        Args:
            calendar: Objet Calendar iCal
            days_ahead: Nombre de jours à l'avance à récupérer (défaut: 30)

        Returns:
            Liste de dictionnaires avec les créneaux
        """
        events = []
        now = datetime.now(self.timezone)
        end_date = now + timedelta(days=days_ahead)

        for component in calendar.walk():
            if component.name == "VEVENT":
                try:
                    dtstart = component.get('dtstart').dt
                    dtend = component.get('dtend').dt
                    summary = str(component.get('summary', ''))

                    if isinstance(dtstart, datetime):
                        if dtstart.tzinfo is None:
                            dtstart = self.timezone.localize(dtstart)
                        else:
                            dtstart = dtstart.astimezone(self.timezone)

                    if isinstance(dtend, datetime):
                        if dtend.tzinfo is None:
                            dtend = self.timezone.localize(dtend)
                        else:
                            dtend = dtend.astimezone(self.timezone)

                    if isinstance(dtstart, datetime) and isinstance(dtend, datetime):
                        if dtend >= now and dtstart <= end_date:
                            status = self._determine_status(summary)

                            events.append({
                                'start': dtstart,
                                'end': dtend,
                                'summary': summary,
                                'status': status,
                                'day_of_week': dtstart.weekday(),
                                'start_time': dtstart.strftime('%H:%M'),
                                'end_time': dtend.strftime('%H:%M')
                            })

                except Exception as e:
                    print(f"Erreur lors du parsing d'un événement: {e}")
                    continue

        return events

    def _determine_status(self, summary: str) -> str:
        summary_lower = summary.lower()

        if 'cours :' in summary_lower or 'cours:' in summary_lower:
            return 'lunch'

        if 'formation' in summary_lower:
            return 'business_trip'

        if 'réunion' in summary_lower or 'reunion' in summary_lower:
            return 'do_not_disturb'

        if 'serv :' in summary_lower:
            return 'away'

        return 'do_not_disturb'

    def sync_extension_from_ical(self, extension, ical_url: str) -> bool:
        """
        Synchronise le planning d'une extension depuis son URL iCal

        Args:
            extension: Objet Extension de la base de données
            ical_url: URL du flux iCal

        Returns:
            True si succès, False sinon
        """
        from app.models import db, Schedule

        logger.info(f"Début de synchronisation iCal pour extension {extension.number}")

        calendar = self.fetch_ical(ical_url)
        if not calendar:
            logger.error("Échec de récupération du calendrier")
            return False

        events = self.parse_events(calendar)
        logger.info(f"{len(events)} événements parsés")

        deleted_count = Schedule.query.filter_by(extension_id=extension.id, source='ical').delete()
        logger.info(f"{deleted_count} anciens créneaux iCal supprimés")

        for event in events:
            schedule = Schedule(
                extension_id=extension.id,
                specific_date=event['start'].date(),
                day_of_week=None,
                start_time=event['start_time'],
                end_time=event['end_time'],
                status=event['status'],
                source='ical'
            )
            db.session.add(schedule)
            logger.debug(f"Ajout créneau: {event['start'].date()} {event['start_time']}-{event['end_time']} ({event['status']})")

        extension.ical_url = ical_url
        extension.last_ical_sync_at = datetime.utcnow()

        try:
            db.session.commit()
            logger.info(f"Synchronisation réussie: {len(events)} créneaux importés")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la synchronisation iCal: {e}")
            return False
