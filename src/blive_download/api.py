from ctypes import sizeof
import json
import datetime, time
import re
import logging
import os
from typing import Callable, Dict, Tuple
from isodate import duration_isoformat

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

def my_request(url) -> Dict:
    res = http.request('Get', url)
    content = res.data
    return json.loads(content.decode())

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

def room_id(short_id):
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
    ws_dict={'uid': 0, 'roomid': roomid, 'protover': 2, 'platform': 'web', 'clientver': '2.5.7', 'type': 2, 'key': key}
    bytes_3 = json.dumps(ws_dict)
    bytes_2 = '\x00\x10\x00\x01\x00\x00\x00\x07\x00\x00\x00\x01'
    length = len(bytes_2 + bytes_3) + 4
    bytes_1 = bytes([length // pow(256, 3) % 256, length // pow(256, 2) % 256, length // pow(256, 1) % 256, length // pow(256, 0) % 256])
    opening = bytes_1 + bytes(bytes_2 + bytes_3, encoding='utf-8')
    return opening

def get_stream_url(uid):
    stream_api = "https://api.live.bilibili.com/room/v1/Room/playUrl?cid=%s&quality=4&platform=web"%uid  #quality=4
    
    rtn = my_request(stream_api)
    urls = rtn["data"]["durl"]

    retry_time= 0
    if urls:
        while 1:
            for i in urls:
                for referer in [True,False]:
                    if retry_time >20:
                        return None, None
                    retry_time+=1
                    url = i.get("url")
                    headers = dict()
                    headers['Accept-Encoding'] = 'identity'
                    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36 " 
                    if referer == True:
                        headers['Referer'] = re.findall(r'(https://.*\/).*\.flv', url)[0]
                    
                    return i.get("url"),headers
    return None, None

DURATION_THRESHOLD = 10
SIZE_THRESHOLD = 1000
def record_source(url, file_name, headers, check_func: Callable[[int, float], bool]) -> Tuple[int,int]:
    '''
    Return (status_code, size)
    '''
    if not url:
        return -1, 0
    timeout = 2
    retry_num = 5
    
    try:
        res = http.request(
                        'Get', 
                        url, 
                        headers=headers,
                        retries = urllib3.Retry(total = retry_num, backoff_factor = 0.2),
                        timeout = timeout,
                        preload_content=False
                        )  
    except Exception as e:
        logging.exception(e)
        print("Failed on: ", url)
        return -1, 0
    
    start_time = time.time()
    with open(file_name, 'wb') as f:    
        print('starting download from:\n%s\nto:\n%s' % (url, file_name), datetime.datetime.now())
        size = 0
        n = 0
        now_1=datetime.datetime.now()
        while n < 5:
            duration = time.time() - start_time
            try:
                _buffer = res.read(1024 * 32)
            except Exception as e:
                _buffer = b''
                logging.exception(e)
                print("=============================")
                print(e)
                print("=============================")

            if len(_buffer) == 0:
                print('==========Currently buffer empty!=={}========='.format(n))
                n+=1
                time.sleep(0.2)
                
            else:
                n = 0
                f.write(_buffer)
                size += len(_buffer)
                if now_1 + datetime.timedelta(seconds=10) < datetime.datetime.now() :
                    now_1=datetime.datetime.now()
                    print('{:<4.2f} MB downloaded'.format(size/1024/1024),datetime.datetime.now())
                if check_func(size, duration):
                    print("=============End of the video reached!==============")
                    break
    duration = time.time() - start_time
    print("finnally")
    if res:
        res.release_conn()
        print("res.release_conn()")

    if not os.path.isfile(file_name):
        return -1, 0
    elif (os.path.getsize(file_name) <= SIZE_THRESHOLD or duration <= DURATION_THRESHOLD):
        os.remove(file_name)
        print(f"os.remove({file_name})")
        return -1, 0

    return 0, size

def record_ffmpeg(url, file_name, headers, check_func: Callable[[int, float], bool]) -> Tuple[int,int]:
    '''
    Record through FFmpeg. FFmpeg must be installed and accessible via the $PATH environment variable

    Return (status_code, size)
    '''
    del headers

    import subprocess
    process = subprocess.run(['ffmpeg', '-version'], stdout= subprocess.PIPE)
    if process.returncode:
        raise FileNotFoundError("FFmpeg not found. FFmpeg must be installed and accessible via the $PATH environment variable")

    print(f'starting FFmpeg from:\n{url}\nto:\n{file_name}', datetime.datetime.now())
    
    import ffmpeg
    input = ffmpeg.input(url)
    output = ffmpeg.output(input, file_name, acodec='copy', vcodec='copy', loglevel = 'warning')
    # run: subprocess.Popen = output.run_async(cmd=['ffmpeg','-loglevel','quiet'])
    run: subprocess.Popen = output.run_async()
    try:
        start_time = time.time()
        now_1 = datetime.datetime.now()
        prev_size = 0
        while True:
            time.sleep(2)
            duration = time.time() - start_time
            size = 0 if not os.path.isfile(file_name) else os.path.getsize(file_name)

            
            if run.poll() is None:
                if check_func(size, duration):
                    print("=============End of the video reached!==============")
                    break
                if size == prev_size:
                    print("=============URL timeout!==============")
                    break
                if now_1 + datetime.timedelta(seconds=10) < datetime.datetime.now() :
                    now_1=datetime.datetime.now()
                    print('{:<4.2f} MB downloaded'.format(size/1024/1024),datetime.datetime.now())
            else:
                print("=============FFmpeg terminated!==============")
                break
            prev_size = size
    finally:
        run.terminate()
    
    
    if not os.path.isfile(file_name):
        return -1, 0
    elif (os.path.getsize(file_name) <= SIZE_THRESHOLD or duration <= DURATION_THRESHOLD):
        os.remove(file_name)
        print(f"os.remove({file_name})")
        return -1, 0

    return 0, size
    
        
    
    
    