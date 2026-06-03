import os
import json
import threading
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required

settings_bp = Blueprint('settings', __name__)

# File paths (project root)
_ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CLIENT_PATH  = os.path.join(_ROOT, 'gdrive_client.json')
TOKEN_PATH   = os.path.join(_ROOT, 'gdrive_token.json')
SCOPES       = ['https://www.googleapis.com/auth/drive.file']


def _folder_id():
    return os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '')


def _is_connected():
    if not os.path.exists(TOKEN_PATH):
        return False
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        return creds.valid
    except Exception:
        return False


def _last_backup():
    """Find most recent backup filename from Drive or local token mtime."""
    if not os.path.exists(TOKEN_PATH):
        return None
    import datetime
    mtime = os.path.getmtime(TOKEN_PATH)
    return datetime.datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')


@settings_bp.route('/settings')
@login_required
def index():
    connected   = _is_connected()
    has_client  = os.path.exists(CLIENT_PATH)
    folder_id   = _folder_id()
    return render_template('settings/index.html',
        connected=connected,
        has_client=has_client,
        folder_id=folder_id,
    )


@settings_bp.route('/settings/upload-client', methods=['POST'])
@login_required
def upload_client():
    f = request.files.get('client_file')
    if not f or not f.filename.endswith('.json'):
        flash('Please upload a valid JSON file.', 'danger')
        return redirect(url_for('settings.index'))
    try:
        content = json.loads(f.read().decode())
        # Validate it's an OAuth client file
        if 'installed' not in content and 'web' not in content:
            raise ValueError('Not a valid OAuth client JSON')
        with open(CLIENT_PATH, 'w') as out:
            json.dump(content, out)
        flash('OAuth client uploaded successfully! ✅', 'success')
    except Exception as e:
        flash(f'Invalid file: {e}', 'danger')
    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/save-folder', methods=['POST'])
@login_required
def save_folder():
    folder_id = request.form.get('folder_id', '').strip()
    if not folder_id:
        flash('Folder ID cannot be empty.', 'danger')
        return redirect(url_for('settings.index'))

    # Persist to a simple config file in project root
    config_path = os.path.join(_ROOT, 'gdrive_config.json')
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
    config['folder_id'] = folder_id
    with open(config_path, 'w') as f:
        json.dump(config, f)

    # Also set in environment for this process
    os.environ['GOOGLE_DRIVE_FOLDER_ID'] = folder_id
    flash('Folder ID saved! ✅', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/auth/google')
@login_required
def auth_google():
    if not os.path.exists(CLIENT_PATH):
        flash('Upload the OAuth client JSON first.', 'warning')
        return redirect(url_for('settings.index'))

    # Allow HTTP for local dev
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(CLIENT_PATH, scopes=SCOPES)
    flow.redirect_uri = url_for('settings.auth_callback', _external=True)

    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['oauth_state'] = state
    return redirect(auth_url)


@settings_bp.route('/settings/auth/google/callback')
@login_required
def auth_callback():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(
        CLIENT_PATH, scopes=SCOPES, state=session.get('oauth_state'))
    flow.redirect_uri = url_for('settings.auth_callback', _external=True)

    try:
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        flash('Google Drive connected successfully! 🎉', 'success')
    except Exception as e:
        flash(f'Authorization failed: {e}', 'danger')

    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/backup-now', methods=['POST'])
@login_required
def backup_now():
    # Load folder_id from config file if not in env
    config_path = os.path.join(_ROOT, 'gdrive_config.json')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
        os.environ['GOOGLE_DRIVE_FOLDER_ID'] = config.get('folder_id', '')

    from app.utils.google_drive import backup_to_drive
    backup_to_drive()
    flash('Backup started — check Google Drive in ~15 seconds. ✅', 'info')
    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/disconnect', methods=['POST'])
@login_required
def disconnect():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
    flash('Google Drive disconnected.', 'info')
    return redirect(url_for('settings.index'))
