# -*- coding: utf_8 -*-

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from logging import getLogger, basicConfig
import json
import os
from datetime import datetime,timedelta,date
from dateutil.relativedelta import relativedelta
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
LOGGING_LEVEL = settings.LOGGING_LEVEL
LOG_FILENAME = settings.LOG_FILENAME

# logger setting
logger = getLogger(__name__)
basicConfig(filename=LOG_FILENAME,
            format='%(asctime)s : [%(levelname)s] [%(filename)s] %(message)s', level=LOGGING_LEVEL)


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
    nowd=date.today()
    logger.debug('datetime.now() : %s', now)
    nextPageTokenMediaItems = ''
    while True:
        queryBody = getQueryBody(nextPageTokenMediaItems, now, QUERY_FILTER)
        mediaItems = service.mediaItems().search(body=queryBody).execute()
        logger.debug('mediaItems length = %s', len(mediaItems))
        if len(mediaItems) == 0:
            logger.info('mediaItems nothing')
            break
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
    logger.debug('photos length = %s', len(photos))
    logger.debug('videos length = %s', len(videos))
    return photos, videos

def getDate(referenceDate: datetime, pastYear: int, pastMonth: int, pastDay: int) -> datetime:
    day = referenceDate - relativedelta(years=pastYear) - relativedelta(months=pastMonth) -relativedelta(days=pastDay)
    return day


def getQueryBody(nextPageTokenMediaItems, referenceDate: datetime, isFilter: bool):
    """
    GooglePhotoAPIに接続するときのquery bodyを生成する

    Returns
    ----------
    body : dict[str,any]
        query body
    """
    logger.info('getQueryBody : isFilter = %s', isFilter)
    if not isFilter:
        body = {
            'pageSize': 50,
            'pageToken': nextPageTokenMediaItems
        }
        logger.debug('Query Body is...')
        logger.debug(body)
        return body
    
    # startDateの計算
    startDate = getDate(referenceDate,PAST_YEARS,PAST_MONTHS,PAST_DAYS)
    logger.info('startDate is %s', startDate)
    body = {
        'pageSize': 50,
        "filters": {
            "dateFilter": {
                "ranges": [
                    {
                        "startDate": {
                            "year": startDate.year,
                            "month": startDate.month,
                            "day": startDate.day
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
    logger.debug('Query Body is...')
    logger.debug(body)
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
        logger.info('download videos')
    else:
        logger.info('download photos')
    if not os.path.exists(TMP_DIR):
        os.mkdir(TMP_DIR)
        logger.warning(
            'created [%s] because the folder did not exist', TMP_DIR)
    ids = []
    for item in mediaItems:
        logger.debug('download : ',item['url']+suffix, TMP_DIR+'/'+item['filename'])
        urllib.request.urlretrieve(
            item['url']+suffix, TMP_DIR+'/'+item['filename'])
        ids.append(item['id'])
    logger.info('%s media downloads completed', len(ids))
    return ids


def toJsonFromIds(ids: list) -> None:
    """
    download済みのIdをリストとしてファイルに出力する
    """
    logger.debug('aquired_media_list : %s', AQUIRED_MEDIA_LIST)
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
        logger.debug('loadIdsJson : aquired media list size = %s', len(result))
    else:
        logger.warning('loadIdsJson: not file exist %s', AQUIRED_MEDIA_LIST)
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
    logger.debug('removeAquiredMedia : result list counts = %s', len(result))
    return result


def moveFiles(destinationPath):
    """
    TMP_DIRにダウンロードしたファイルを
    destinationPathにmoveする
    """
    try:
        for p in glob.glob(TMP_DIR+'/*', recursive=False):
            shutil.move(p, destinationPath)
        logger.info('done file moving')
    except shutil.Error as e:
        logger.error('shutil.Error: Destination path')
        logger.error(e)
        logger.warning('failed file moving')


def main():
    logger.info('start script')
    # クレデンシャルを取得
    credentials = getCredentials()
    service = build(
        API_SERVICE_NAME,
        API_VERSION,
        credentials=credentials, static_discovery=False
    )
    # mediaIdを取得
    logger.info('start : get media ids')
    photos, videos = getMediaIds(service)
    logger.info('end : get media ids')

    # 取得済みのメディアを削除
    logger.info('start : remove aquired media ids')
    acquiredIds = loadIdsJson()
    photos = removeAquiredMedia(photos, acquiredIds)
    videos = removeAquiredMedia(videos, acquiredIds)
    logger.info('end : remove aquired media ids')

    # メディアのダウンロード
    logger.info('start : download media')
    photoIds = downloadMedia(photos, False)
    videoIds = downloadMedia(videos, True)
    logger.info('end : download media')

    # バックアップフォルダへの移動
    logger.info('start : move files')
    moveFiles(DESTINATION_DIR)
    logger.info('end : move files')

    # 取得済みリストの更新
    logger.info('start : update aquired list json')
    result = []
    result.extend(photoIds)
    result.extend(videoIds)
    result.extend(acquiredIds)
    toJsonFromIds(result)
    logger.info('end : update aquired list json')

    logger.info('All Proccess Complete!')


if __name__ == "__main__":
    main()
