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
import settings

# variable declaration
SCOPES = settings.SCOPES
API_SERVICE_NAME = settings.API_SERVICE_NAME
API_VERSION = settings.API_VERSION
CLIENT_SECRET_FILE = settings.CLIENT_SECRET_FILE
CREDENTIAL_FILE = settings.CREDENTIAL_FILE
AQUIRED_MEDIA_LIST = settings.AQUIRED_MEDIA_LIST
TMP_DIR = settings.TMP_DIR
DESTINATION_DIR = settings.DESTINATION_DIR
QUERY_FILTER = settings.QUERY_FILTER
PAST_YEARS = settings.PAST_YEARS
PAST_MONTHS = settings.PAST_MONTHS
PAST_DAYS = settings.PAST_DAYS


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
    photos : list
        id,filename,url
    videos : list
        id,filename,url
    """
    photos = []
    videos = []
    now = datetime.now()
    nextPageTokenMediaItems = ''
    while True:
        queryBody = getQueryBody(nextPageTokenMediaItems, now, QUERY_FILTER)
        mediaItems = service.mediaItems().search(body=queryBody).execute()
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


def getQueryBody(nextPageTokenMediaItems, referenceDate, isFilter: bool) -> dict[str, any]:
    """
    GooglePhotoAPIに接続するときのquery bodyを生成する

    Returns
    ----------
    body : dict[str,any]
        query body
    """
    if not isFilter:
        body = {
            'pageSize': 50,
            'pageToken': nextPageTokenMediaItems
        }
        return body

    body = {
        'pageSize': 50,
        "filters": {
            "dateFilter": {
                "ranges": [
                    {
                        "startDate": {
                            "year": referenceDate.year - PAST_YEARS,
                            "month": referenceDate.month - PAST_MONTHS,
                            "day": referenceDate.day - PAST_DAYS
                        },
                        "endDate": {
                            "year": referenceDate.year,
                            "month": referenceDate.month,
                            "day": referenceDate.day,
                        },
                    },
                ],
            },
        },
        'pageToken': nextPageTokenMediaItems
    }
    return body


def downloadMedia(mediaItems: list, isVideo: bool) -> list:
    """
    GooglePhotoAPIに接続しphotoもしくはvideoをダウンロードする

    Parameters
    ----------
    mediaItems : list
        メディア(photo or video)のリスト
    isVideo : bool
        ビデオであるかどうか

    Returns
    ----------
    ids : list
        ダウンロードに成功したidのリスト
    """
    suffix: str = '=d'
    if isVideo:
        suffix = '=dv'
    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)
    ids = []
    for item in mediaItems:
        urllib.request.urlretrieve(
            item['url']+suffix, TMP_DIR+'/'+item['filename'])
        ids.append(item['id'])
    return ids


def toJsonFromIds(ids: list) -> None:
    """
    download済みのIdをリストとしてファイルに出力する
    """
    with open(AQUIRED_MEDIA_LIST, 'w') as f:
        json.dump(ids, f, ensure_ascii=False)


def loadIdsJson() -> list:
    """
    download済みのIdリストを読み込む
    """
    result = []
    if os.path.exists(AQUIRED_MEDIA_LIST):
        with open(AQUIRED_MEDIA_LIST) as f_credential_r:
            result = json.loads(f_credential_r.read())
    return result


def removeAquiredMedia(mediaItems: list, ids: list) -> list:
    """
    download済みのitemを除去する

    Parameters
    ----------
    mediaItems : list
        メディア(photo or video)のリスト
    ids : list
        download済みのidのリスト
    """
    result = []
    for item in mediaItems:
        tmp = {}
        if not item['id'] in ids:
            tmp['id'], tmp['url'], tmp['filename'] = item['id'], item['url'], item['filename']
            result.append(tmp)
    return result


def moveFiles(destinationPath):
    """
    TMP_DIRにダウンロードしたファイルを
    destinationPathにmoveする
    """
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
    moveFiles(DESTINATION_DIR)

    # 取得済みリストの更新
    result = []
    result.extend(photoIds)
    result.extend(videoIds)
    result.extend(acquiredIds)
    toJsonFromIds(result)


if __name__ == "__main__":
    main()
