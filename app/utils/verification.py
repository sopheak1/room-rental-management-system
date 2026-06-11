import hmac
import hashlib
from flask import current_app


def generate_payment_hash(receipt_number, remaining_balance, amount, payment_date, payment_method):
    """Short verification code for a payment, derived from the receipt number,
    the remaining balance after this payment, and this payment's own details.
    Recomputed on every payment, so each payment in a receipt's history keeps
    its own permanent code."""
    msg = f"{receipt_number}|{remaining_balance}|{amount}|{payment_date.isoformat()}|{payment_method or ''}"
    secret = current_app.config['SECRET_KEY']
    digest = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    code = digest[:8].upper()
    return f"{code[:4]}-{code[4:]}"
