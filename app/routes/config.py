from flask import Blueprint, render_template
from app.models import Config

config_bp = Blueprint('config', __name__, url_prefix='/config')


@config_bp.route('/')
def index():
    config = Config.query.first()
    return render_template('config.html', config=config)
