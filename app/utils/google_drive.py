import os
import io
import json
import sqlite3
import threading
from datetime import datetime

def backup_to_drive():
    """
    Safely backup rental.db to Google Drive using SQLite's built-in backup API.
    Runs in a background thread — never slows down the main request.

    Required environment variables:
      GOOGLE_SERVICE_ACCOUNT_JSON  — full JSON content of the service account key
      GOOGLE_DRIVE_FOLDER_ID       — Google Drive folder ID to upload into
    """
    def _run():
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

        # Support both: file path OR inline JSON string
        key_path  = os.environ.get('GOOGLE_SERVICE_ACCOUNT_PATH')
        sa_json   = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

        if key_path and os.path.exists(key_path):
            with open(key_path) as f:
                sa_json = f.read()

        if not sa_json or not folder_id:
            return  # not configured — skip silently

        db_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'instance', 'rental.db'
        )
        if not os.path.exists(db_path):
            return

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload

            # ── Safe SQLite backup into memory ─────────────────────
            # Uses SQLite's backup API — safe even during active writes
            backup_buf = io.BytesIO()
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(':memory:')
            src.backup(dst)
            src.close()
            # Serialize in-memory DB to bytes
            for chunk in dst.iterdump():
                pass  # ensure fully loaded
            dst.close()

            # Re-read to bytes properly
            src = sqlite3.connect(db_path)
            dst_file = io.BytesIO()
            dst_conn = sqlite3.connect(':memory:')
            src.backup(dst_conn)
            src.close()
            # Write memory DB to BytesIO
            tmp_path = db_path + '.bak'
            backup_conn = sqlite3.connect(tmp_path)
            with sqlite3.connect(db_path) as src2:
                src2.backup(backup_conn)
            backup_conn.close()

            # ── Upload to Google Drive ──────────────────────────────
            creds = service_account.Credentials.from_service_account_info(
                json.loads(sa_json),
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            service = build('drive', 'v3', credentials=creds, cache_discovery=False)

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

            # Upload the safe backup copy
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename  = f"rental_backup_{timestamp}.db"

            with open(tmp_path, 'rb') as f:
                media = MediaIoBaseUpload(f, mimetype='application/octet-stream', resumable=False)
                service.files().create(
                    body={'name': filename, 'parents': [folder_id]},
                    media_body=media,
                    fields='id'
                ).execute()

            # Clean up temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        except Exception:
            pass  # silent fail — never break the main request

    threading.Thread(target=_run, daemon=True).start()
