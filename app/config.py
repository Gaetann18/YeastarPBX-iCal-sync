import os
from datetime import timedelta
from pathlib import Path


class Config:
    """Configuration de l'application Flask"""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'

    basedir = Path(__file__).parent.parent.resolve()

    @staticmethod
    def build_database_uri():
        if os.environ.get('DATABASE_URL'):
            return os.environ.get('DATABASE_URL')
        db_type = os.environ.get('DB_TYPE', 'sqlite').lower()
        if db_type == 'sqlite':
            db_path = Config.basedir / 'instance' / 'app.db'
            db_path_str = str(db_path).replace('\\', '/')
            return f'sqlite:///{db_path_str}'
        elif db_type == 'mysql':
            db_host = os.environ.get('DB_HOST', 'localhost')
            db_port = os.environ.get('DB_PORT', '3306')
            db_name = os.environ.get('DB_NAME', 'yeastar')
            db_user = os.environ.get('DB_USER', 'root')
            db_password = os.environ.get('DB_PASSWORD', '')
            return f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4'
        elif db_type == 'postgresql':
            db_host = os.environ.get('DB_HOST', 'localhost')
            db_port = os.environ.get('DB_PORT', '5432')
            db_name = os.environ.get('DB_NAME', 'yeastar')
            db_user = os.environ.get('DB_USER', 'postgres')
            db_password = os.environ.get('DB_PASSWORD', '')
            return f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        else:
            db_path = Config.basedir / 'instance' / 'app.db'
            db_path_str = str(db_path).replace('\\', '/')
            return f'sqlite:///{db_path_str}'

    SQLALCHEMY_DATABASE_URI = build_database_uri.__func__()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_API_ENABLED = False  
    TIMEZONE = 'Europe/Paris'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = str(basedir / 'instance' / 'uploads')

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
