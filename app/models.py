from datetime import datetime, date
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Building(db.Model):
    __tablename__ = 'buildings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rooms = db.relationship('Room', backref='building', lazy=True, cascade='all, delete-orphan')


class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.Integer, default=1)
    room_type = db.Column(db.String(20), default='single')  # single, double, studio
    price = db.Column(db.Float, nullable=False)
    deposit_amount = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenants = db.relationship('Tenant', backref='room', lazy=True)
    history = db.relationship('TenantHistory', backref='room', lazy=True)
    receipts = db.relationship('Receipt', backref='room', lazy=True)

    @property
    def active_tenant(self):
        return Tenant.query.filter_by(room_id=self.id, is_active=True).first()


class Tenant(db.Model):
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(10))
    nid = db.Column(db.String(50))
    tel = db.Column(db.String(20))
    emergency_contact_name = db.Column(db.String(150))
    emergency_contact_tel = db.Column(db.String(20))
    num_roommates = db.Column(db.Integer, default=1)
    contract_duration = db.Column(db.String(20), default='monthly')
    move_in_date = db.Column(db.Date)
    deposit_paid = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    receipts = db.relationship('Receipt', backref='tenant', lazy=True)


class TenantHistory(db.Model):
    __tablename__ = 'tenant_history'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    name = db.Column(db.String(150))
    gender = db.Column(db.String(10))
    nid = db.Column(db.String(50))
    tel = db.Column(db.String(20))
    num_roommates = db.Column(db.Integer)
    move_in_date = db.Column(db.Date)
    move_out_date = db.Column(db.Date)
    move_out_reason = db.Column(db.Text)
    deposit_paid = db.Column(db.Float)
    deposit_refunded = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UtilityPrice(db.Model):
    __tablename__ = 'utility_prices'
    id = db.Column(db.Integer, primary_key=True)
    utility_type = db.Column(db.String(20), nullable=False)  # water, electricity
    price_per_unit = db.Column(db.Float, nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Receipt(db.Model):
    __tablename__ = 'receipts'
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(20), unique=True, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    billing_month = db.Column(db.Integer, nullable=False)
    billing_year = db.Column(db.Integer, nullable=False)
    room_price = db.Column(db.Float, nullable=False)
    electricity_from = db.Column(db.Float, nullable=True)
    electricity_to = db.Column(db.Float, nullable=True)
    electricity_units = db.Column(db.Float, nullable=True)
    electricity_price_per_unit = db.Column(db.Float, nullable=True)
    electricity_total = db.Column(db.Float, default=0)
    water_from = db.Column(db.Float, nullable=True)
    water_to = db.Column(db.Float, nullable=True)
    water_units = db.Column(db.Float, nullable=True)
    water_price_per_unit = db.Column(db.Float, nullable=True)
    water_total = db.Column(db.Float, default=0)
    previous_balance = db.Column(db.Float, default=0)
    late_fee = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0)
    remaining_balance = db.Column(db.Float, default=0)
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid, paid, partial
    payment_method = db.Column(db.String(20), nullable=True)  # cash, bank_transfer, qr
    payment_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payment_logs = db.relationship('PaymentLog', backref='receipt', lazy=True,
                                   order_by='PaymentLog.created_at')

    @property
    def billing_label(self):
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        return f"{months[self.billing_month - 1]} {self.billing_year}"


class PaymentLog(db.Model):
    __tablename__ = 'payment_logs'
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('receipts.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=True)
    payment_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
