from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Import all sub-modules so their routes register on api_bp
from app.routes.api import auth   # noqa: F401, E402
from app.routes.api import sync   # noqa: F401, E402
from app.routes.api import rooms, tenants, receipts, payments, utility_usage, conflicts  # noqa: F401, E402
