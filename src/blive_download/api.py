import json
import datetime, time
import logging
import os
import traceback
from typing import Callable, Dict, Optional, Tuple

import urllib3

HEADERS = {
    'Accept-Encoding': 'identity',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.62 Safari/537.36',
}

#https://urllib3.readthedocs.io/en/stable/reference/urllib3.poolmanager.html#urllib3.PoolManager
#connection_pool_kw: https://urllib3.readthedocs.io/en/stable/reference/urllib3.connectionpool.html#urllib3.connectionpool.ConnectionPool
http = urllib3.PoolManager(
    num_pools = 10,
    maxsize = 5,
    headers = HEADERS,
    retries = urllib3.Retry(total = 5, backoff_factor = 0.2),
    timeout = 2
)

def my_request(url, fields = None) -> Dict:
    res = http.request('Get', url, fields = fields)
    content = res.data
    try:
        rtn = json.loads(content.decode())
        return rtn
    except:
        print(traceback.format_exc())
        print(content.decode())
        return dict()

def is_live(roomid):
    live_api = "https://api.live.bilibili.com/room/v1/Room/room_init?id=%s"%str(roomid)
    rtn = my_request(live_api)
    live_status = rtn["data"]["live_status"]
    if live_status == 0:
        return False
    elif live_status == 2:
        return False
    elif live_status == 1:
        return True
    else:
        raise Exception(f"live_status as {live_status}, not 0,1,2")

def get_room_id(short_id):
    live_api = "https://api.live.bilibili.com/room/v1/Room/room_init?id=%s"%str(short_id)
    rtn = my_request(live_api)
    return rtn["data"]["room_id"]

def get_ws_host(roomid:int) -> str:
    ws_host_api = "https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={}&type=0".format(roomid)
    rtn = my_request(ws_host_api)
    return rtn["data"]["host_list"][0]['host']

def ws_key(roomid):   #return the key for websocket connection
    danmu_api = "https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={}&platform=pc&player=web".format(roomid)
    rtn = my_request(danmu_api)
    return rtn["data"]["token"]

def ws_open_msg(roomid):  #return the first message for websocket connection
    key = ws_key(roomid)
    #protocol see https://daidr.me/archives/code-526.html
    # protover 3 is available
    ws_dict={'uid': 0, 'roomid': roomid, 'protover': 2, 'platform': 'web', 'clientver': '2.5.7', 'type': 2, 'key': key}
    bytes_3 = json.dumps(ws_dict)
    bytes_2 = '\x00\x10\x00\x01\x00\x00\x00\x07\x00\x00\x00\x01'
    length = len(bytes_2 + bytes_3) + 4
    bytes_1 = bytes([length // pow(256, 3) % 256, length // pow(256, 2) % 256, length // pow(256, 1) % 256, length // pow(256, 0) % 256])
    opening = bytes_1 + bytes(bytes_2 + bytes_3, encoding='utf-8')
    return opening

def get_room_info(roomid:int) -> Dict:
    room_info = "https://api.live.bilibili.com/room/v1/Room/get_info?room_id={}".format(roomid)
    rtn = my_request(room_info).get("data", dict())
    return rtn

# https://github.com/biliup/biliup/blob/b6c718155d095d6306b2c85e73fb25271e8bf510/biliup/plugins/bilibili.py
def get_stream_url(uid) -> Optional[str]:
    params = {
        'room_id': uid,
        'qn': '10000',
        'platform': 'web',
        'codec': '0,1',
        'protocol': '0,1',
        'format': '0,1,2',
        'ptype': '8',
        'dolby': '5'
    }                    
    res = my_request("https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo", fields=params)
    if res['code'] != 0:
        return None
    if not res['data']['playurl_info']:
        return None

    data = res['data']['playurl_info']['playurl']['stream'][0]['format'][0]['codec'][0]
    stream_number = 0
    if "mcdn" in data['url_info'][0]['host']:
        stream_number += 1
    stream_url:str = data['url_info'][stream_number]['host'] + data['base_url'] + data['url_info'][stream_number]['extra']
    return stream_url
    
