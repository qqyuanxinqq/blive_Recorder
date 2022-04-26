import urllib
import json
import re
import time
import logging

def my_request(url):
    headers = dict()
    headers['Accept-Encoding'] = 'identity'
    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko'
    
    req = urllib.request.Request(url,headers=headers)  # type: ignore
    
    max_retry = 10
    for retry_num in range(max_retry):
        try:
            res = urllib.request.urlopen(req, timeout=10) # type: ignore
            break
        except urllib.error.URLError as e: # type: ignore
            # logging.exception(e)
            print("During retry" , retry_num , "=============================")
            print(e)
            print("=============================")
            time.sleep(2)
            if retry_num >= max_retry-1:
                raise e
        
    content = res.read() # type: ignore
    return json.loads(content.decode())

def is_live(roomid):
    live_api = "https://api.live.bilibili.com/room/v1/Room/room_init?id=%s"%str(roomid)
    rtn = my_request(live_api)
    live_status = rtn["data"]["live_status"]
    #print(rtn)
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


def ws_key(roomid):   #return the key for websocket connection
    danmu_api = "https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={}&platform=pc&player=web".format(roomid)
    rtn = my_request(danmu_api)
    return rtn.get("data").get("token")   

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
    urls = rtn.get("data").get("durl")
    #print(urls)
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
