import csv
import json
from io import StringIO
from datetime import datetime


class PlanningParser:
    DAY_MAPPING = {
        'lundi': 0, 'monday': 0,
        'mardi': 1, 'tuesday': 1,
        'mercredi': 2, 'wednesday': 2,
        'jeudi': 3, 'thursday': 3,
        'vendredi': 4, 'friday': 4,
        'samedi': 5, 'saturday': 5,
        'dimanche': 6, 'sunday': 6
    }

    @staticmethod
    def parse_csv(content: str):
        results = []
        errors = []

        try:
            reader = csv.DictReader(StringIO(content))

            required_columns = ['extension', 'day', 'start_time', 'end_time']
            if not all(col in reader.fieldnames for col in required_columns):
                return None, f"Colonnes requises manquantes. Attendues: {', '.join(required_columns)}"

            for i, row in enumerate(reader, start=2):
                try:
                    extension = row['extension'].strip()
                    day_str = row['day'].strip().lower()
                    start_time = row['start_time'].strip()
                    end_time = row['end_time'].strip()
                    status = row.get('status', 'available').strip()

                    day_of_week = PlanningParser.DAY_MAPPING.get(day_str)
                    if day_of_week is None:
                        errors.append(f"Ligne {i}: Jour invalide '{row['day']}'")
                        continue

                    try:
                        datetime.strptime(start_time, '%H:%M')
                        datetime.strptime(end_time, '%H:%M')
                    except ValueError:
                        errors.append(f"Ligne {i}: Format d'heure invalide (attendu HH:MM)")
                        continue

                    results.append({
                        'extension': extension,
                        'day_of_week': day_of_week,
                        'start_time': start_time,
                        'end_time': end_time,
                        'status': status
                    })

                except Exception as e:
                    errors.append(f"Ligne {i}: {str(e)}")

        except Exception as e:
            return None, f"Erreur de lecture CSV: {str(e)}"

        if errors:
            return results, f"Importé avec {len(errors)} erreur(s): " + "; ".join(errors[:3])

        return results, f"{len(results)} créneaux importés avec succès"

    @staticmethod
    def parse_json(content: str):
        results = []
        errors = []

        try:
            data = json.loads(content)

            if not isinstance(data, list):
                data = [data]

            for i, ext_data in enumerate(data):
                extension = ext_data.get('extension')
                schedules = ext_data.get('schedules', [])

                if not extension:
                    errors.append(f"Entrée {i+1}: Extension manquante")
                    continue

                for j, schedule in enumerate(schedules):
                    try:
                        day_str = schedule.get('day', '').lower()
                        start_time = schedule.get('start', '')
                        end_time = schedule.get('end', '')
                        status = schedule.get('status', 'available')

                        day_of_week = PlanningParser.DAY_MAPPING.get(day_str)
                        if day_of_week is None:
                            errors.append(f"Extension {extension}, créneau {j+1}: Jour invalide '{day_str}'")
                            continue

                        try:
                            datetime.strptime(start_time, '%H:%M')
                            datetime.strptime(end_time, '%H:%M')
                        except ValueError:
                            errors.append(f"Extension {extension}, créneau {j+1}: Format d'heure invalide")
                            continue

                        results.append({
                            'extension': extension,
                            'day_of_week': day_of_week,
                            'start_time': start_time,
                            'end_time': end_time,
                            'status': status
                        })

                    except Exception as e:
                        errors.append(f"Extension {extension}, créneau {j+1}: {str(e)}")

        except json.JSONDecodeError as e:
            return None, f"Erreur de parsing JSON: {str(e)}"
        except Exception as e:
            return None, f"Erreur: {str(e)}"

        if errors:
            return results, f"Importé avec {len(errors)} erreur(s): " + "; ".join(errors[:3])

        return results, f"{len(results)} créneaux importés avec succès"

    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        try:
            datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False
