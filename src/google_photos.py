# -*- coding: utf_8 -*-

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import json
import os
import pprint
from datetime import datetime
import urllib.request
import shutil
import glob

SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
API_SERVICE_NAME = 'photoslibrary'
API_VERSION = 'v1'
CLIENT_SECRET_FILE = 'client_secret.json'
CREDENTIAL_FILE = 'credential.json'
AQUIRED_MEDIA_LIST = 'aquired_list.json'
TMP_DIR = 'tmp'
DESTINATION_DIR = 'gpbk'


def support_datetime_default(o: object) -> None:
    """
    ファイル書き込み時の日付表示指定

    Parameter
    ---------
    o : object
    """
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(repr(o) + " is not JSON serializable")


def getCredentials():
    """
    API接続時にクレデンシャルを取得する。
    初回はclient_secret.jsonをもとに認証を行い
    ユーザー操作の後credential.jsonを生成する
    次回以降はcredential.jsonをもとに認証を行う

    Returns
    ----------
    credential : Any
        クレデンシャル情報
    """
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


def getMediaIds(service):
    """
    API接続時にクレデンシャルを取得する。
    初回はclient_secret.jsonをもとに認証を行い
    ユーザー操作の後credential.jsonを生成する
    次回以降はcredential.jsonをもとに認証を行う

    Parameters
    ----------
    service : int
        credentialsから生成したAPI接続用のservice

    Returns
    ----------
    photos : dict
    videos : dict
    """
    photos = []
    videos = []
    now = datetime.now()
    nextPageTokenMediaItems = ''
    while True:
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
        for mediaItem in mediaItems['mediaItems']:
            photo = {}
            video = {}
            if 'photo' in mediaItem['mediaMetadata']:
                photo['id'], photo['filename'], photo['url'] = mediaItem['id'], mediaItem[
                    'filename'], mediaItem['baseUrl']
                photos.append(photo)
            else:
                video['id'], video['filename'], video['url'] = mediaItem['id'], mediaItem[
                    'filename'], mediaItem['baseUrl']
                videos.append(video)
        if 'nextPageToken' in mediaItems:
            nextPageTokenMediaItems = mediaItems['nextPageToken']
        else:
            break

    return photos, videos


def downloadMedia(mediaDict: dict, isVideo: bool) -> list:
    suffix: str = '=d'
    if isVideo:
        suffix = '=dv'
    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)
    ids = []
    for item in mediaDict:
        urllib.request.urlretrieve(
            item['url']+suffix, TMP_DIR+'/'+item['filename'])
        ids.append(item['id'])
    return ids


def toJsonFromIds(ids: list) -> None:
    with open(AQUIRED_MEDIA_LIST, 'w') as f:
        json.dump(ids, f, ensure_ascii=False)


def loadIdsJson() -> list:
    result = []
    if os.path.exists(AQUIRED_MEDIA_LIST):
        with open(AQUIRED_MEDIA_LIST) as f_credential_r:
            result = json.loads(f_credential_r.read())
    return result


def removeAquiredMedia(mediaItems: list, ids: list) -> list:
    result = []
    for item in mediaItems:
        tmp = {}
        if not item['id'] in ids:
            tmp['id'], tmp['url'], tmp['filename'] = item['id'], item['url'], item['filename']
            result.append(tmp)
    return result


def moveFiles(destinationPath):
    for p in glob.glob(TMP_DIR+'/*', recursive=False):
        shutil.move(p, destinationPath)


def main():
    # クレデンシャルを取得
    credentials = getCredentials()
    service = build(
        API_SERVICE_NAME,
        API_VERSION,
        credentials=credentials, static_discovery=False
    )
    # mediaIdを取得
    photos, videos = getMediaIds(service)

    # 取得済みのメディアを削除
    acquiredIds = loadIdsJson()
    photos = removeAquiredMedia(photos, acquiredIds)
    videos = removeAquiredMedia(videos, acquiredIds)

    # メディアのダウンロード
    photoIds = downloadMedia(photos, False)
    videoIds = downloadMedia(videos, True)

    # バックアップフォルダへの移動
    moveFiles('/gpbk')

    # 取得済みリストの更新
    result = []
    result.extend(photoIds)
    result.extend(videoIds)
    result.extend(acquiredIds)
    toJsonFromIds(result)

    # pprint.pprint(photos)
    # pprint.pprint(videos)
    # print('photos :'+str(len(photos))+',videos :'+str(len(videos)))
    # result: dict = service.mediaItems().list(pageSize=1).execute()
    # print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
