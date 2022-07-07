from datetime import datetime
from . import cipher
from urllib import parse
import os
import math
import hashlib
from ...utils.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
import base64
from time import sleep
import json
import sys
from filelock import FileLock
import requests


# From PC ugc_assisstant
APPKEY = 'aae92bc66f3edfab'
APPSECRET = 'af125a0d5279fd576c1b4418a3e8276d'

# upload chunk size = 2MB
CHUNK_SIZE = 2 * 1024 * 1024

# captcha
CAPTCHA_RECOGNIZE_URL = "http://66.112.209.22:8889/captcha"

class VideoPart:
    """
    Video Part of a post.
    每个对象代表一个分P

    Attributes:
        path: file path in local file system.
        title: title of the video part.
        desc: description of the video part.
        server_file_name: file name in bilibili server. generated by pre-upload API.
    """
    def __init__(self, path, title='', desc='', server_file_name=None):
        self.path = path
        self.title = title
        self.desc = desc
        self.server_file_name=server_file_name

    def __repr__(self):
        return '<{clazz}, path: {path}, title: {title}, desc: {desc}, server_file_name:{server_file_name}>'\
            .format(clazz=self.__class__.__name__,
                    path=self.path,
                    title=self.title,
                    desc=self.desc,
                    server_file_name=self.server_file_name)


def get_key(sid=None, jsessionid=None):
    """
    get public key, hash and session id for login.
    Args:
        sid: session id. only for captcha login.
        jsessionid: j-session id. only for captcha login.
    Returns:
        hash: salt for password encryption.
        pubkey: rsa public key for password encryption.
        sid: session id.
    """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': "application/json, text/javascript, */*; q=0.01"
    }
    post_data = {
        'appkey': APPKEY,
        'platform': "pc",
        'ts': str(int(datetime.now().timestamp()))
    }
    post_data['sign'] = cipher.sign_dict(post_data, APPSECRET)
    cookie = {}
    if sid:
        cookie['sid'] = sid
    if jsessionid:
        cookie['JSESSIONID'] = jsessionid
    r = requests.post(
        "https://passport.bilibili.com/api/oauth2/getKey",
        headers=headers,
        data=post_data,
        cookies=cookie,
        timeout = 60,
    )
    r_data = r.json()['data']
    if sid:
        return r_data['hash'], r_data['key'], sid
    return r_data['hash'], r_data['key'], r.cookies['sid']


def get_capcha(sid):
    headers = {
        'User-Agent': '',
        'Accept-Encoding': 'gzip,deflate',
    }

    params = {
        'appkey': APPKEY,
        'platform': 'pc',
        'ts': str(int(datetime.now().timestamp()))
    }
    params['sign'] = cipher.sign_dict(params, APPSECRET)

    r = requests.get(
        "https://passport.bilibili.com/captcha",
        headers=headers,
        params=params,
        cookies={
            'sid': sid
        },
        timeout = 60,
    )

    print(r.status_code)

    capcha_data = r.content

    return r.cookies['JSESSIONID'], capcha_data


def recognize_captcha(img: bytes):
    img_base64 = str(base64.b64encode(img), encoding='utf-8')
    r = requests.post(
        url=CAPTCHA_RECOGNIZE_URL,
        data={'image': img_base64},
        timeout = 60,
    )
    return r.content.decode()


def login(username, password):
    """
    bilibili login.
    Args:
        username: plain text username for bilibili.
        password: plain text password for bilibili.

    Returns:
        code: login response code (0: success, -105: captcha error, ...).
        access_token: token for further operation.
        refresh_token: token for refresh access_token.
        sid: session id.
        mid: member id.
        expires_in: access token expire time (30 days)
    """
    hash, pubkey, sid = get_key()

    encrypted_password = cipher.encrypt_login_password(password, hash, pubkey)
    url_encoded_username = parse.quote_plus(username)
    url_encoded_password = parse.quote_plus(encrypted_password)

    post_data = {
        'appkey': APPKEY,
        'password': url_encoded_password,
        'platform': "pc",
        'ts': str(int(datetime.now().timestamp())),
        'username': url_encoded_username
    }

    post_data['sign'] = cipher.sign_dict(post_data, APPSECRET)
    # avoid multiple url parse
    post_data['username'] = username
    post_data['password'] = encrypted_password  # type: ignore

    headers = {
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': '',
        'Accept-Encoding': 'gzip,deflate',
    }

    r = requests.post(
        "https://passport.bilibili.com/api/oauth2/login",
        headers=headers,
        data=post_data,
        cookies={
            'sid': sid
        },
        timeout = 60,
    )
    response = r.json()
    response_code = response['code']
    if response_code == 0:
        login_data = response['data']
        return response_code, login_data['access_token'], login_data['refresh_token'], sid, login_data['mid'], login_data["expires_in"]
    elif response_code == -105: # captcha error, retry=5
        retry_cnt = 5
        while response_code == -105 and retry_cnt > 0:
            response_code, access_token, refresh_token, sid, mid, expire_in = login_captcha(username, password, sid)
            if response_code == 0:
                return response_code, access_token, refresh_token, sid, mid, expire_in
            retry_cnt -= 1

    # other error code
    return response_code, None, None, sid, None, None


def login_captcha(username, password, sid):
    """
    bilibili login with captcha.
    depend on captcha recognize service, please do not use this as first choice.
    Args:
        username: plain text username for bilibili.
        password: plain text password for bilibili.
        sid: session id
    Returns:
        code: login response code (0: success, -105: captcha error, ...).
        access_token: token for further operation.
        refresh_token: token for refresh access_token.
        sid: session id.
        mid: member id.
        expires_in: access token expire time (30 days)
    """

    jsessionid, captcha_img = get_capcha(sid)
    captcha_str = recognize_captcha(captcha_img)

    hash, pubkey, sid = get_key(sid, jsessionid)

    encrypted_password = cipher.encrypt_login_password(password, hash, pubkey)
    url_encoded_username = parse.quote_plus(username)
    url_encoded_password = parse.quote_plus(encrypted_password)

    post_data = {
        'appkey': APPKEY,
        'captcha': captcha_str,
        'password': url_encoded_password,
        'platform': "pc",
        'ts': str(int(datetime.now().timestamp())),
        'username': url_encoded_username
    }

    post_data['sign'] = cipher.sign_dict(post_data, APPSECRET)
    # avoid multiple url parse
    post_data['username'] = username
    post_data['password'] = encrypted_password  # type: ignore
    post_data['captcha'] = captcha_str

    headers = {
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': '',
        'Accept-Encoding': 'gzip,deflate',
    }

    r = requests.post(
        "https://passport.bilibili.com/api/oauth2/login",
        headers=headers,
        data=post_data,
        cookies={
            'JSESSIONID': jsessionid,
            'sid': sid
        },
        timeout = 60,
    )
    response = r.json()
    if response['code'] == 0:
        login_data = response['data']
        return response['code'], login_data['access_token'], login_data['refresh_token'], sid, login_data['mid'], login_data["expires_in"]
    else:
        return response['code'], None, None, sid, None, None


def login_by_access_token(access_token):
    """
    bilibili access token login.
    Args:
        access_token: Bilibili access token got by previous username/password login.

    Returns:
        sid: session id.
        mid: member id.
        expires_in: access token expire time
    """
    headers = {
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip,deflate',
        'Host': 'passport.bilibili.com',
        'User-Agent': '',
    }

    login_params = {
        'appkey': APPKEY,
        'access_token': access_token,
        'platform': "pc",
        'ts': str(int(datetime.now().timestamp())),
    }
    login_params['sign'] = cipher.sign_dict(login_params, APPSECRET)

    r = requests.get(
        url="https://passport.bilibili.com/api/oauth2/info",
        headers=headers,
        params=login_params,
        timeout = 60,
    )
    print(r.content)
    login_data = r.json()['data']

    return r.cookies['sid'], login_data['mid'], login_data["expires_in"]


def upload_cover(access_token, sid, cover_file_path):
    with open(cover_file_path, "rb") as f:
        cover_pic = f.read()

    headers = {
        'Connection': 'keep-alive',
        'Host': 'member.bilibili.com',
        'Accept-Encoding': 'gzip,deflate',
        'User-Agent': '',
    }

    params = {
        "access_key": access_token,
    }

    params["sign"] = cipher.sign_dict(params, APPSECRET)

    files = {
        'file': ("cover.png", cover_pic, "Content-Type: image/png"),
    }

    r = requests.post(
        "http://member.bilibili.com/x/vu/client/cover/up",
        headers=headers,
        params=params,
        files=files,
        cookies={
            'sid': sid
        },
        verify=False,
        timeout = 60,
    )

    return r.json()["data"]["url"]

def chunk_gen(local_file_name):
    '''
    First return file info
    Then starting to yield chunk and chunk info
    '''
    
    file_size = os.path.getsize(local_file_name)
    chunk_total_num = int(math.ceil(file_size / CHUNK_SIZE))
    def generator():
        with open(local_file_name, 'rb') as f:
            for chunk_id in range(0, chunk_total_num):
                chunk_data = f.read(CHUNK_SIZE)
                yield chunk_id,chunk_data
    return  file_size,chunk_total_num, generator()


def upload_chunk(upload_url, server_file_name, local_file_name, chunk_data, chunk_size, chunk_id, chunk_total_num, max_retry = 5):
    """
    upload video chunk.
    Args:
        upload_url: upload url by pre_upload api.
        server_file_name: file name on server by pre_upload api.
        local_file_name: video file name in local fs.
        chunk_data: binary data of video chunk.
        chunk_size: default of ugc_assisstant is 2M.
        chunk_id: chunk number.
        chunk_total_num: total chunk number.

    Returns:
        True: upload chunk success.
        False: upload chunk fail.
    """
    print("chunk{}/{}".format(chunk_id, chunk_total_num))
    print("filename: {}".format(local_file_name))
    files = {
        'version': (None, '2.0.0.1054'),
        'filesize': (None, chunk_size),
        'chunk': (None, chunk_id),
        'chunks': (None, chunk_total_num),
        'md5': (None, cipher.md5_bytes(chunk_data)),
        'file': (local_file_name, chunk_data, 'application/octet-stream')
    }
    status, r = Retry(max_retry=max_retry, check_func= check_upload_chunk).run(
        requests.post,
        url=upload_url,
        files=files,
        cookies={
            'PHPSESSID': server_file_name
        },
        timeout = 60,        
    )   
    return status

def check_upload_chunk(r):
    if r.status_code == 200 and r.json()['OK'] == 1:
        return True
    else:
        print("Failed: "+r.content.decode())
        return False


def upload_video_part(access_token, sid, mid, video_part: VideoPart, max_retry=5, thread_pool_workers = 1):
    """
    upload a video file.
    Args:
        access_token: access token generated by login api.
        sid: session id.
        mid: member id.
        video_part: local video file data.
        max_retry: max retry number for each chunk.

    Returns:
        status: success or fail.
        server_file_name: server file name by pre_upload api.
    """
    if video_part.server_file_name:
        print('video part {} exists. The server_file_name is: {}'.format(video_part.path, video_part.server_file_name))
        return True
    
    headers = {
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': '',
        'Accept-Encoding': 'gzip,deflate',
    }

    status, r = Retry(max_retry=max_retry).run(
        requests.get,
        "http://member.bilibili.com/preupload?access_key={}&mid={}&profile=ugcfr%2Fpc3".format(access_token, mid),
        headers=headers,
        cookies={
            'sid': sid
        },
        verify=False,
        timeout = 60,   
    )   

    pre_upload_data = r.json()
    upload_url = pre_upload_data['url']
    print(f"Upload to \n {upload_url}")
    complete_upload_url = pre_upload_data['complete']
    server_file_name = pre_upload_data['filename']
    local_file_name = video_part.path
    file_size,chunk_total_num, chunk_generator = chunk_gen(local_file_name)

    file_hash = hashlib.md5()
     
    with ThreadPoolExecutor(max_workers=thread_pool_workers) as tpe:
        t_list = set()
        readed_chunks = 0
        while readed_chunks < chunk_total_num or t_list:
            while len(t_list)<= thread_pool_workers:
                try:
                    chunk_id,chunk_data = next(chunk_generator)
                    file_hash.update(chunk_data)
                    readed_chunks +=1
                except StopIteration:
                    break
                
                t_obj = tpe.submit(
                    upload_chunk,
                    upload_url,
                    server_file_name,
                    os.path.basename(local_file_name),
                    chunk_data,
                    CHUNK_SIZE,
                    chunk_id,
                    chunk_total_num,
                    max_retry
                )
                t_list.add(t_obj)
            
            done, t_list = wait(t_list, return_when = "FIRST_COMPLETED")

            for t in done:
                if not t.result():
                    print("upload failed in upload_video_part for: ", local_file_name)
                    return False
            # print(t_list)
        
    print(file_hash.hexdigest())

    post_data = {
        'chunks': chunk_total_num,
        'filesize': file_size,
        'md5': file_hash.hexdigest(),
        'name': os.path.basename(local_file_name),
        'version': '2.0.0.1054',
    }

    r = requests.post(
        url=complete_upload_url,
        data=post_data,
        headers=headers,
        timeout = 60,
    )
    print("video part finished, status code:", r.status_code)

    video_part.server_file_name = server_file_name
    print('video part {} finished. The server_file_name is: {}'.format(video_part.path, server_file_name), flush=True)
    return True

def record_info_fromjson(video_list_json):
    with FileLock(video_list_json + '.lock'):
        with open(video_list_json, 'r') as f:
            record_info = json.load(f)
    return record_info

def record_info_dumptojson(record_info):
    filename = record_info['filename']
    with FileLock(filename+".lock"):
        with open(filename, 'w') as f:
            json.dump(record_info, f, indent=4)

def upload(
        access_token,
        sid,
        mid,
        avid,
        bvid,
        parts,
        copyright: int,
        title: str,
        tid: int,
        tag: str,
        desc: str,
        source: str = '',
        cover: str = '',
        no_reprint: int = 0,
        open_elec: int = 1,
        max_retry: int = 5,
        thread_pool_workers: int = 1,
        video_list_json = '',
        submit_mode = 1):
    """
    insert videos into existed post.

    Args:
        access_token: oauth2 access token.
        sid: session id.
        mid: member id.
        avid: av number,
        bvid: bv string,
        parts: VideoPart list.
        insert_index: new video index.
        copyright: 原创/转载.
        title: 投稿标题.
        tid: 分区id.
        tag: 标签.
        desc: 投稿简介.
        source: 转载地址.
        cover: cover url.
        no_reprint: 可否转载.
        open_elec: 充电.
        max_retry: max retry time for each chunk.
        thread_pool_workers: max upload threads.
        video_list_json: This file will be frequently checked for dynamic realtime parts uploading. 
        mode: 1(default): single submission, 2: submission after each video part

    Returns:
        (aid, bvid)
        aid: av号
        bvid: bv号
    """
    if submit_mode == 1:
        print("single submission mode")
    elif submit_mode ==2:
        print("submission after each video part")


    if not avid and not bvid:
        print("Add new video post")
    else:
        print('Replace existing video post: Avid: {}, Bvid: {}'.format(avid, bvid))
        if not avid:
            avid = cipher.bv2av(bvid)

    # cover
    if os.path.isfile(cover):
        try:
            cover = upload_cover(access_token, sid, cover)
        except:
            cover = ''
    else:
        cover = '' 
    submit_data = {
        'build': 1054,
        'copyright': copyright,
        'cover': cover,
        'desc': desc,
        'no_reprint': no_reprint,
        'open_elec': open_elec,
        'source': source,
        'tag': tag,
        'tid': tid,
        'title': title,
        'videos': []
    }
    
    if not isinstance(parts, list):
        parts = [parts]
    dynamic_update = bool(video_list_json)
    post_videos_num = 0

    # parts is dynamic updating
    while True:
        if len(parts) != post_videos_num:
            for video_part in parts[post_videos_num::]:
                print("upload {} now".format(video_part.path))
                status = upload_video_part(access_token, sid, mid, video_part, max_retry,thread_pool_workers)
                if not status:
                    print("upload failed")
                    return None, None
                post_videos_num += 1
                if submit_mode == 2:
                    avid, bvid = submit_videos(access_token, sid, parts[0:post_videos_num], submit_data, avid)
        
        if not dynamic_update:
            print("No dynamic record_info json file provided, stop waiting for new videos.")
            break
        else:
        #     print("Trakcing provided record_info json file.")
            sleep(40)
            sys.stdout.flush()
            record_info = record_info_fromjson(video_list_json)
            directory = record_info.get('directory')
            file_list=record_info.get('videolist')
            for item in file_list[post_videos_num::]:
                parts.append(VideoPart(
                    path=os.path.join(directory, item),
                    title = item.split('.')[0]
                ))
            if record_info.get("Status", "Done") == "Living":
                print("The live is still on, waiting for new videos.")
            else:
                print("The live is done, stop waiting for new videos.")
                dynamic_update = False
    if submit_mode == 1:
        avid, bvid = submit_videos(access_token, sid, parts, submit_data, avid)

    print("Done! All {} videos uploaded!".format(post_videos_num))

    return avid, bvid

@Retry(max_retry = 5, interval = 1).decorator
def get_post_data(access_token, sid, avid):
    headers = {
        'Connection': 'keep-alive',
        'Host': 'member.bilibili.com',
        'Accept-Encoding': 'gzip,deflate',
        'User-Agent': '',
    }

    params = {
        "access_key": access_token,
        "aid": avid,
        "build": "1054"
    }

    params["sign"] = cipher.sign_dict(params, APPSECRET)

    r = requests.get(
        url="http://member.bilibili.com/x/client/archive/view",
        headers=headers,
        params=params,
        cookies={
            'sid': sid
        },
        timeout = 60,
    )

    print(r.content.decode())
    return r.json()["data"]

# def replace_videos(
#         access_token,
#         sid,
#         mid,
#         avid,
#         bvid,
#         parts,
#         copyright: int,
#         title: str,
#         tid: int,
#         tag: str,
#         desc: str,
#         source: str = '',
#         cover: str = '',
#         no_reprint: int = 0,
#         open_elec: int = 1,
#         max_retry: int = 5,
#         thread_pool_workers: int = 1,
#         video_list_json = '',
#         mode = 2):
#     """
#     insert videos into existed post.

#     Args:
#         access_token: oauth2 access token.
#         sid: session id.
#         mid: member id.
#         avid: av number,
#         bvid: bv string,
#         parts: VideoPart list.
#         insert_index: new video index.
#         copyright: 原创/转载.
#         title: 投稿标题.
#         tid: 分区id.
#         tag: 标签.
#         desc: 投稿简介.
#         source: 转载地址.
#         cover: cover url.
#         no_reprint: 可否转载.
#         open_elec: 充电.
#         max_retry: max retry time for each chunk.
#         thread_pool_workers: max upload threads.

#     Returns:
#         (aid, bvid)
#         aid: av号
#         bvid: bv号
#     """


#     if not avid and not bvid:
#         print("please provide avid or bvid")
#         return None, None

#     if not avid:
#         avid = cipher.bv2av(bvid)
#     # cover
#     if os.path.isfile(cover):
#         try:
#             cover = upload_cover(access_token, sid, cover)
#         except:
#             cover = ''
#     else:
#         cover = '' 
#     submit_data = {
#         'build': 1054,
#         'copyright': copyright,
#         'cover': cover,
#         'desc': desc,
#         'no_reprint': no_reprint,
#         'open_elec': open_elec,
#         'source': source,
#         'tag': tag,
#         'tid': tid,
#         'title': title,
#         'videos': []
#     }
    
#     if not isinstance(parts, list):
#         parts = [parts]
#     dynamic_update = bool(video_list_json)
#     post_videos_num = 0

#     # parts is dynamic updating
#     while True:
#         if len(parts) != post_videos_num:
#             for video_part in parts[post_videos_num::]:
#                 print("upload {} now".format(video_part.path))
#                 status = upload_video_part(access_token, sid, mid, video_part, max_retry,thread_pool_workers)
#                 print("video part {} finished, status: {}".format(video_part.path, status), flush=True)
#                 if not status:
#                     print("upload failed")
#                     return None, None
#             post_videos_num = len(parts)
#             if mode == 2:
#                 avid, bvid = submit_videos(access_token, sid, parts, submit_data, avid)
        
#         if not dynamic_update:
#             print("No dynamic record_info json file provided, stop waiting for new videos.")
#             break
#         else:
#         #     print("Trakcing provided record_info json file.")
#             sleep(40)
#             sys.stdout.flush()
#             record_info = record_info_fromjson(video_list_json)
#             directory = record_info.get('directory')
#             file_list=record_info.get('videolist')
#             for item in file_list[post_videos_num::]:
#                 parts.append(VideoPart(
#                     path=os.path.join(directory, item),
#                     title = item.split('.')[0]
#                 ))
#             if record_info.get("Status", "Done") == "Living":
#                 print("The live is still on, waiting for new videos.")
#             else:
#                 print("The live is done, stop waiting for new videos.")
#                 dynamic_update = False
#     if mode == 1:
#         avid, bvid = submit_videos(access_token, sid, parts, submit_data, avid)

#     print("Done! All {} videos uploaded!".format(post_videos_num))

#     return avid, bvid
@Retry(max_retry = 3, interval = 10).decorator
def submit_videos(access_token, sid, parts, submit_data, avid = None):
    '''
    Return avid, bvid
    '''
    
    if avid:
        avid = int(avid)
    # Load previously submitted data
        post_video_data = get_post_data(access_token, sid, avid)
        old_data = {
            'aid': avid,
            'build': 1054,
            'copyright': post_video_data["archive"]["copyright"],
            'cover': post_video_data["archive"]["cover"],
            'desc': post_video_data["archive"]["desc"],
            'no_reprint': post_video_data["archive"]["no_reprint"],
            'open_elec': post_video_data["archive_elec"]["state"], # open_elec not tested
            'source': post_video_data["archive"]["source"],
            'tag': post_video_data["archive"]["tag"],
            'tid': post_video_data["archive"]["tid"],
            'title': post_video_data["archive"]["title"],
            'videos': post_video_data["videos"]
        }
        # edit archive data
        if submit_data.get('copyright'):
            old_data["copyright"] = submit_data.get('copyright')
        if submit_data.get('title'):
            old_data["title"] = submit_data.get('title')
        if submit_data.get('tid'):
            old_data["tid"] = submit_data.get('tid')
        if submit_data.get('tag'):
            old_data["tag"] = submit_data.get('tag')
        if submit_data.get('desc'):
            old_data["desc"] = submit_data.get('desc')
        if submit_data.get('source'):
            old_data["source"] = submit_data.get('source')
        if submit_data.get('cover'):
            old_data["cover"] = submit_data.get('cover')
        if submit_data.get('no_reprint'):
            old_data["no_reprint"] = submit_data.get('no_reprint')
        if submit_data.get('open_elec'):
            old_data["open_elec"] = submit_data.get('open_elec')
        submit_data = old_data

    submit_data['videos'] = []
    for video_part in parts:
        submit_data['videos'].append({
            "desc": video_part.desc,
            "filename": video_part.server_file_name,
            "title": video_part.title
        })

    headers = {
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'User-Agent': '',
    }
    params = {
        'access_key': access_token,
    }
    params['sign'] = cipher.sign_dict(params, APPSECRET)
    
    if avid:
        r = requests.post(
            url="http://member.bilibili.com/x/vu/client/edit",
            params=params,
            headers=headers,
            verify=False,
            cookies={
                'sid': sid
            },
            json=submit_data,
            timeout = 60,
        )
    else:
        r = requests.post(
            url="http://member.bilibili.com/x/vu/client/add",
            params=params,
            headers=headers,
            verify=False,
            cookies={
                'sid': sid
            },
            json=submit_data,
            timeout = 60,
        )
    print("Current {} videos submitted, status code: {}".format(len(parts), r.status_code), flush=True)
    print(r.content.decode())
    

    data = r.json()["data"]
    return data["aid"], data["bvid"]

