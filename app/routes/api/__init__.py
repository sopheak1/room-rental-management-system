from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Import all sub-modules so their routes register on api_bp
from app.routes.api import auth  # noqa: F401, E402
