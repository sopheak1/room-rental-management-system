import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rental-secret-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'rental.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    EXCHANGE_RATE = 4000  # 1 USD = 4,000 ៛
