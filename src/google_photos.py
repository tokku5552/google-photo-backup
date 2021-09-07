# google_photos.py
import google.oauth2.credentials
import google_auth_oauthlib.flow
import json
import os
from datetime import datetime, date
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
API_SERVICE_NAME = 'photoslibrary'
API_VERSION = 'v1'
CLIENT_SECRET_FILE = 'client_secret.json'
CREDENTIAL_FILE = 'credential.json'


def support_datetime_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(repr(o) + " is not JSON serializable")


def getCredentials():
    if os.path.exists(CREDENTIAL_FILE):
        with open(CREDENTIAL_FILE) as f_credential_r:
            credentials_json = json.loads(f_credential_r.read())
            credentials = google.oauth2.credentials.Credentials(
                credentials_json['token'],
                refresh_token=credentials_json['_refresh_token'],
                token_uri=credentials_json['_token_uri'],
                client_id=credentials_json['_client_id'],
                client_secret=credentials_json['_client_secret']
            )
    else:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE, scopes=SCOPES)

        credentials = flow.run_console()
    with open(CREDENTIAL_FILE, mode='w') as f_credential_w:
        f_credential_w.write(json.dumps(
            vars(credentials), default=support_datetime_default, sort_keys=True))

    return credentials


def main():
    credentials = getCredentials()
    service = build(
        API_SERVICE_NAME,
        API_VERSION,
        credentials=credentials
    )


if __name__ == "__main__":
    main()
