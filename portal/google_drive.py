import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def upload_submission(uploaded_file, filename):
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not all([client_id, client_secret, refresh_token, folder_id]):
        raise RuntimeError(
            "Google Drive environment variables are not configured."
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        uploaded_file,
        mimetype=uploaded_file.content_type or "application/octet-stream",
        resumable=True,
    )

    result = service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,webViewLink",
        supportsAllDrives=True,
    ).execute()

    return result["webViewLink"]
