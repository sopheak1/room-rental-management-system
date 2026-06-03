import os
import json
import sqlite3
import shutil
import threading
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, send_file
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


@settings_bp.route('/settings/test', methods=['POST'])
@login_required
def test_connection():
    """Upload a tiny test file to Drive and delete it — confirms everything works."""
    folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '')
    if not folder_id:
        flash('Folder ID not set. Complete Step 2 first.', 'warning')
        return redirect(url_for('settings.index'))

    if not _is_connected():
        flash('Not connected to Google Drive. Complete Step 3 first.', 'warning')
        return redirect(url_for('settings.index'))

    try:
        import io
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)

        # Upload a tiny test file
        content = b'Google Drive backup test - rental management system'
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype='text/plain')
        f = service.files().create(
            body={'name': 'test_connection.txt', 'parents': [folder_id]},
            media_body=media,
            fields='id, name'
        ).execute()

        # Delete it right away
        service.files().delete(fileId=f['id']).execute()

        flash('✅ Google Drive connection test passed! Upload and delete both worked.', 'success')

    except Exception as e:
        flash(f'❌ Test failed: {e}', 'danger')

    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/download-db')
@login_required
def download_db():
    """Download a safe copy of the current database."""
    db_path = os.path.join(_ROOT, 'instance', 'rental.db')
    if not os.path.exists(db_path):
        flash('Database file not found.', 'danger')
        return redirect(url_for('settings.index'))

    # Create a safe backup copy using SQLite backup API
    tmp_path = db_path + '.download'
    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(tmp_path)
        src.backup(dst)
        src.close()
        dst.close()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=f'rental_backup_{timestamp}.db',
            mimetype='application/octet-stream'
        )
    except Exception as e:
        flash(f'Download failed: {e}', 'danger')
        return redirect(url_for('settings.index'))
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@settings_bp.route('/settings/upload-db', methods=['POST'])
@login_required
def upload_db():
    """Restore the database from an uploaded .db file."""
    f = request.files.get('db_file')
    if not f or not f.filename.endswith('.db'):
        flash('Please upload a valid .db file.', 'danger')
        return redirect(url_for('settings.index'))

    db_path = os.path.join(_ROOT, 'instance', 'rental.db')

    try:
        # Save uploaded file to a temp location
        tmp_path = db_path + '.restore'
        f.save(tmp_path)

        # Validate it's a real SQLite database
        conn = sqlite3.connect(tmp_path)
        conn.execute('SELECT name FROM sqlite_master LIMIT 1')
        conn.close()

        # Backup current DB before replacing
        if os.path.exists(db_path):
            shutil.copy2(db_path, db_path + '.prev')

        # Replace database
        shutil.move(tmp_path, db_path)
        flash('✅ Database restored successfully! The previous DB was saved as rental.db.prev', 'success')

    except sqlite3.DatabaseError:
        flash('❌ Invalid database file — not a valid SQLite database.', 'danger')
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    except Exception as e:
        flash(f'❌ Restore failed: {e}', 'danger')

    return redirect(url_for('settings.index'))


@settings_bp.route('/settings/disconnect', methods=['POST'])
@login_required
def disconnect():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
    flash('Google Drive disconnected.', 'info')
    return redirect(url_for('settings.index'))
