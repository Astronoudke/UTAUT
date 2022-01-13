from flask import Blueprint

bp = Blueprint('new_study', __name__)

from app.create_study import routes