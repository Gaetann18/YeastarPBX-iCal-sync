from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Config(db.Model):
    __tablename__ = 'config'

    id = db.Column(db.Integer, primary_key=True)
    pbx_url = db.Column(db.String(255), nullable=False)
    client_id = db.Column(db.String(255), nullable=False)
    client_secret_encrypted = db.Column(db.Text, nullable=False)
    default_unavailable_status = db.Column(db.String(50), default='available')
    sync_interval_minutes = db.Column(db.Integer, default=5)
    access_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Extension(db.Model):
    __tablename__ = 'extensions'

    id = db.Column(db.Integer, primary_key=True)
    yeastar_id = db.Column(db.Integer, nullable=False, unique=True)
    number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    current_status = db.Column(db.String(50))
    last_synced_at = db.Column(db.DateTime)
    planning_enabled = db.Column(db.Boolean, default=False)
    override_enabled = db.Column(db.Boolean, default=False)  
    ical_token = db.Column(db.String(255))
    ical_url = db.Column(db.Text)
    last_ical_sync_at = db.Column(db.DateTime) 


    schedules = db.relationship('Schedule', backref='extension', lazy=True, cascade='all, delete-orphan')
    overrides = db.relationship('Override', backref='extension', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('Log', backref='extension', lazy=True, cascade='all, delete-orphan')


class Schedule(db.Model):
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    extension_id = db.Column(db.Integer, db.ForeignKey('extensions.id'), nullable=False)

    day_of_week = db.Column(db.Integer)  # 0=lundi, 6=dimanche (NULL si date spécifique)
    specific_date = db.Column(db.Date)  # Date spécifique (NULL si récurrent)

    start_time = db.Column(db.String(5), nullable=False)  # Format HH:MM
    end_time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(50), default='available')
    source = db.Column(db.String(20), default='manual')  # 'manual' 'ical' 'csv'


class Override(db.Model):
    __tablename__ = 'overrides'

    id = db.Column(db.Integer, primary_key=True)
    extension_id = db.Column(db.Integer, db.ForeignKey('extensions.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    extension_id = db.Column(db.Integer, db.ForeignKey('extensions.id'))
    action = db.Column(db.String(255), nullable=False)
    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50))
    trigger_type = db.Column(db.String(50))  # 'schedule' 'override' 'manual' 'api_error'
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
