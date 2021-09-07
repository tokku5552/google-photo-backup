# -*- coding: utf_8 -*-

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import json
import os
import pprint
from datetime import datetime, date


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


def getPhotos(service):
    photos = []
    now = datetime.now()
    nextPageTokenMediaItems = ''
    while True:
        photo = {}
        body = {
            'pageSize': 50,
            "filters": {
                "dateFilter": {
                    "ranges": [
                        {
                            "startDate": {
                                "year": now.year,
                                "month": now.month - 1,
                                "day": now.day
                            },
                            "endDate": {
                                "year": now.year,
                                "month": now.month,
                                "day": now.day,
                            },
                        },
                    ],
                },
            },
            'pageToken': nextPageTokenMediaItems
        }
        mediaItems = service.mediaItems().search(body=body).execute()
        # pprint.pprint(mediaItems)
        for mediaItem in mediaItems['mediaItems']:
            photo['id'], photo['filename'], photo['url'] = mediaItem['id'], mediaItem['filename'], mediaItem['baseUrl']
            pprint.pprint(mediaItem)
            photos.append(photo)
        if 'nextPageToken' in mediaItems:
            nextPageTokenMediaItems = mediaItems['nextPageToken']
        else:
            break
    pprint.pprint(photos)


def main():
    credentials = getCredentials()
    service = build(
        API_SERVICE_NAME,
        API_VERSION,
        credentials=credentials, static_discovery=False
    )
    getPhotos(service)
    # result: dict = service.mediaItems().list(pageSize=1).execute()
    # print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
