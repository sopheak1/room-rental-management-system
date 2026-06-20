import os
import click
from flask import Flask, session, redirect, request, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def _migrate(db):
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    if 'rooms' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('rooms')]
        if 'due_day' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE rooms ADD COLUMN due_day INTEGER DEFAULT 1'))
                conn.commit()
    if 'receipts' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('receipts')]
        if 'fee' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE receipts ADD COLUMN fee REAL DEFAULT 0'))
                conn.commit()
    if 'payment_logs' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('payment_logs')]
        if 'deleted_at' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE payment_logs ADD COLUMN deleted_at DATETIME'))
                conn.commit()
        if 'delete_reason' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE payment_logs ADD COLUMN delete_reason TEXT'))
                conn.commit()
        if 'verification_hash' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE payment_logs ADD COLUMN verification_hash VARCHAR(20)'))
                conn.commit()

    # Add updated_at to buildings
    if 'buildings' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('buildings')]
        if 'updated_at' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE buildings ADD COLUMN updated_at DATETIME'))
                conn.execute(text('UPDATE buildings SET updated_at = created_at WHERE updated_at IS NULL'))
                conn.commit()

    # Add updated_at to rooms
    if 'rooms' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('rooms')]
        if 'updated_at' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE rooms ADD COLUMN updated_at DATETIME'))
                conn.execute(text('UPDATE rooms SET updated_at = created_at WHERE updated_at IS NULL'))
                conn.commit()

    # Add updated_at to tenants
    if 'tenants' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('tenants')]
        if 'updated_at' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE tenants ADD COLUMN updated_at DATETIME'))
                conn.execute(text('UPDATE tenants SET updated_at = created_at WHERE updated_at IS NULL'))
                conn.commit()

    # Add updated_at to receipts
    if 'receipts' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('receipts')]
        if 'updated_at' not in cols:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE receipts ADD COLUMN updated_at DATETIME'))
                conn.execute(text('UPDATE receipts SET updated_at = created_at WHERE updated_at IS NULL'))
                conn.commit()

    # Add unique index backing the tenant+room+month duplicate-receipt guard
    if 'receipts' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('receipts')]
        if 'uq_receipts_tenant_room_month' not in existing_indexes:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'CREATE UNIQUE INDEX uq_receipts_tenant_room_month '
                        'ON receipts (tenant_id, room_id, billing_month, billing_year)'
                    ))
                    conn.commit()
            except Exception:
                # If real existing data already has duplicate (tenant_id, room_id,
                # billing_month, billing_year) rows, creating the index will fail.
                # Don't crash app startup over this — skip silently and rely on the
                # app-level check + commit-time IntegrityError guard instead.
                pass


def create_app():  # noqa: C901

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config.Config')
    if os.environ.get('RENTAL_TESTING'):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    from app.utils.request_logging import init_request_logging
    init_request_logging(app)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.unauthorized_handler
    def unauthorized():
        # Clear any broken session data and redirect to login
        session.clear()
        return redirect(url_for('auth.login'))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.buildings import buildings_bp
    from app.routes.rooms import rooms_bp
    from app.routes.tenants import tenants_bp
    from app.routes.utilities import utilities_bp
    from app.routes.utility_usage import utility_usage_bp
    from app.routes.receipts import receipts_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from flask_jwt_extended import JWTManager
    from app.routes.api import api_bp
    from app.routes.api.auth import is_token_revoked

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(buildings_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(tenants_bp)
    app.register_blueprint(utilities_bp)
    app.register_blueprint(utility_usage_bp)
    app.register_blueprint(receipts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return is_token_revoked(jwt_payload)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token required'}), 401

    app.register_blueprint(api_bp)

    # Load Google Drive folder ID from config file if present
    import os as _os, json as _json
    _config_path = _os.path.join(_os.path.abspath(_os.path.dirname(__file__)), '..', 'gdrive_config.json')
    if _os.path.exists(_config_path):
        with open(_config_path) as _f:
            _cfg = _json.load(_f)
        if _cfg.get('folder_id'):
            _os.environ.setdefault('GOOGLE_DRIVE_FOLDER_ID', _cfg['folder_id'])

    with app.app_context():
        db.create_all()
        _migrate(db)

    @app.errorhandler(401)
    def unauthorized_error(e):
        session.clear()
        return redirect(url_for('auth.login'))

    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        # Let normal HTTP errors (404, 405, etc.) pass through — don't convert to 500
        if isinstance(e, HTTPException):
            return e
        # For unexpected errors only: check if session is corrupted
        from flask_login import current_user
        try:
            _ = current_user.is_authenticated
        except Exception:
            session.clear()
            return redirect(url_for('auth.login'))
        raise e

    @app.route('/favicon.ico')
    @app.route('/apple-touch-icon.png')
    @app.route('/apple-touch-icon-precomposed.png')
    def ignore_browser_icons():
        return '', 204  # No Content — silently ignore browser auto-requests

    @app.context_processor
    def inject_lang():
        return {'lang': session.get('lang', 'km')}

    _STATUS_LABELS = {
        'paid':      {'km': 'បានបង់',       'en': 'Paid'},
        'unpaid':    {'km': 'មិនទាន់បង់',   'en': 'Unpaid'},
        'partial':   {'km': 'បង់មួយផ្នែក',  'en': 'Partial'},
        'deferred':  {'km': 'បង់ពន្យារ',    'en': 'Deferred'},
    }

    @app.template_filter('status_label')
    def status_label_filter(value):
        lang = session.get('lang', 'km')
        entry = _STATUS_LABELS.get(value, {})
        return entry.get(lang, value.title() if value else '')

    _DELETE_REASON_LABELS = {
        'wrong_amount': {'km': 'បញ្ចូលទឹកលុយខុស', 'en': 'Wrong amount entered'},
        'wrong_room':   {'km': 'បញ្ចូលខុសបន្ទប់',  'en': 'Wrong room entered'},
    }

    @app.template_filter('delete_reason_label')
    def delete_reason_label_filter(value):
        if not value:
            return ''
        lang = session.get('lang', 'km')
        entry = _DELETE_REASON_LABELS.get(value)
        return entry.get(lang, value) if entry else value

    @app.route('/lang/<code>')
    def set_lang(code):
        if code in ('km', 'en'):
            session['lang'] = code
        return redirect(request.referrer or '/')

    @app.template_filter('khr')
    def khr_filter(value):
        """Format a number as Khmer Riel: 200,000 ៛"""
        if value is None:
            return '0 ៛'
        return f'{int(round(float(value))):,} ៛'

    @app.template_filter('usd')
    def usd_filter(value):
        """Convert KHR amount to USD string using exchange rate."""
        if value is None:
            return '$0.00'
        rate = app.config.get('EXCHANGE_RATE', 4000)
        return f'${float(value) / rate:,.2f}'

    @app.cli.command('create-admin')
    @click.argument('username')
    @click.argument('password')
    @click.option('--name', default='Admin', help='Full name')
    def create_admin(username, password, name):
        """Create an admin user: flask create-admin <username> <password> --name "Full Name" """
        from app.models import User
        if User.query.filter_by(username=username).first():
            click.echo(f'User "{username}" already exists.')
            return
        user = User(username=username, full_name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f'Admin user "{username}" created successfully.')

    return app
