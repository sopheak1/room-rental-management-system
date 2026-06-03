"""
Run this ONCE on your local machine to authorize Google Drive access.
It will open a browser for you to log in with your Google account.
After authorization, gdrive_token.json is saved — upload it to PythonAnywhere.

Usage:
    python3 authorize_gdrive.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app.utils.google_drive import authorize
authorize()
