import os
import sqlite3
import threading
from datetime import datetime

# Paths (can be overridden via env vars)
_DEFAULT_TOKEN  = os.path.join(os.path.dirname(__file__), '..', '..', 'gdrive_token.json')
_DEFAULT_CLIENT = os.path.join(os.path.dirname(__file__), '..', '..', 'gdrive_client.json')


def _get_drive_service():
    """Build an authenticated Drive service using OAuth2 stored token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path  = os.environ.get('GOOGLE_TOKEN_PATH',  _DEFAULT_TOKEN)
    client_path = os.environ.get('GOOGLE_CLIENT_PATH', _DEFAULT_CLIENT)

    if not os.path.exists(token_path):
        raise FileNotFoundError(f"Token not found: {token_path}. Run authorize_gdrive.py first.")

    creds = Credentials.from_authorized_user_file(
        token_path,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )

    # Auto-refresh token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def authorize():
    """
    One-time authorization. Run this once from a machine with a browser.
    Creates gdrive_token.json which is used for all future backups.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_path = os.environ.get('GOOGLE_CLIENT_PATH', _DEFAULT_CLIENT)
    token_path  = os.environ.get('GOOGLE_TOKEN_PATH',  _DEFAULT_TOKEN)

    if not os.path.exists(client_path):
        raise FileNotFoundError(f"OAuth client file not found: {client_path}")

    flow = InstalledAppFlow.from_client_secrets_file(
        client_path,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    creds = flow.run_local_server(port=0)

    with open(token_path, 'w') as f:
        f.write(creds.to_json())

    print(f"✅ Authorization successful! Token saved to: {token_path}")


def backup_to_drive():
    """
    Safely backup rental.db to Google Drive using OAuth2.
    Runs in background thread — never slows down the main request.
    Requires: gdrive_token.json (created by running authorize())
    Optional env vars:
      GOOGLE_TOKEN_PATH   — path to token file (default: project root/gdrive_token.json)
      GOOGLE_DRIVE_FOLDER_ID — Google Drive folder ID
    """
    def _run():
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        if not folder_id:
            return  # not configured

        db_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'instance', 'rental.db'
        )
        if not os.path.exists(db_path):
            return

        try:
            from googleapiclient.http import MediaFileUpload

            service = _get_drive_service()

            # Keep only 10 most recent backups
            existing = service.files().list(
                q=f"'{folder_id}' in parents and name contains 'rental_backup_' and trashed=false",
                fields='files(id, name, createdTime)',
                orderBy='createdTime asc'
            ).execute().get('files', [])

            if len(existing) >= 10:
                for old in existing[:len(existing) - 9]:
                    try:
                        service.files().delete(fileId=old['id']).execute()
                    except Exception:
                        pass

            # Safe SQLite backup to temp file
            tmp_path = db_path + '.bak'
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(tmp_path)
            src.backup(dst)
            src.close()
            dst.close()

            # Upload
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename  = f"rental_backup_{timestamp}.db"
            media = MediaFileUpload(tmp_path, mimetype='application/octet-stream', resumable=False)
            service.files().create(
                body={'name': filename, 'parents': [folder_id]},
                media_body=media,
                fields='id'
            ).execute()

            try:
                os.remove(tmp_path)
            except Exception:
                pass

        except Exception:
            pass  # silent fail

    threading.Thread(target=_run, daemon=True).start()
