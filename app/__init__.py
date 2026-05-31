import click
from flask import Flask, session, redirect, request
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


def create_app():  # noqa: C901

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config.Config')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.buildings import buildings_bp
    from app.routes.rooms import rooms_bp
    from app.routes.tenants import tenants_bp
    from app.routes.utilities import utilities_bp
    from app.routes.receipts import receipts_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(buildings_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(tenants_bp)
    app.register_blueprint(utilities_bp)
    app.register_blueprint(receipts_bp)
    app.register_blueprint(reports_bp)

    with app.app_context():
        db.create_all()
        _migrate(db)

    @app.context_processor
    def inject_lang():
        return {'lang': session.get('lang', 'km')}

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
