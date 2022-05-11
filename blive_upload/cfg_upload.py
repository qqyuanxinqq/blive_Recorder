import os
import json
import logging
from filelock import FileLock
import logging

from .bilibiliuploader.bilibiliuploader import BilibiliUploader
from .bilibiliuploader.core import VideoPart

    
#Edit Information here, details in https://github.com/FortuneDayssss/BilibiliUploader
#此处修改上传内容，标题，简介，tag等，详见https://github.com/FortuneDayssss/BilibiliUploader
def config_gen(record_info, up_name = None) -> dict:
    if not up_name:
        up_name = record_info["up_name"]

    if "example" == up_name:
        configuration = dict(
            username = "username",
            password = "password",
            upload_args = dict(
                copyright=1,
                title='Example Title',
                tid=17,
                tag=",".join(["Some", "Tags"]),
                desc="An example video description",
                video_list_json = record_info.get('filename')))
    elif "kaofish" == up_name:
        configuration = dict(
            username = "username",
            password = "password",
            upload_args = dict(
                copyright=1,
                title='【⭐烤鱼子{}.{}.{}时 录播⭐】摸了摸了'.format(record_info.get('month'),record_info.get('day'), record_info.get('hour')),
                tid=17,
                tag=",".join(["烤鱼", "烤鱼子", "录播", "烤鱼子Official", "烤鱼录播"]),
                desc='''⭐烤鱼子Official⭐{}.{}.{} 直播，单推地址：https://live.bilibili.com/22259479
粉丝群：烤鱼盖浇饭研究协会：784611303，欢迎来摸鱼
本视频系自动上传，欢迎各位在评论区留下游戏内容、分P等相关信息
'''.format(record_info.get('year'), record_info.get('month'),record_info.get('day')),
# (还在为录播迟迟没有更新而烦恼么？https://github.com/qqyuanxinqq/blive_Recorder 快就是快！)
                thread_pool_workers=10,
                max_retry = 10,
                video_list_json = record_info.get('filename'), 
                submit_mode = 2))
    elif up_name == "api":
        configuration = dict(
            username = "username",
            password = "password",
            upload_args = dict(
                copyright=1,
                title='【⭐少年Pi{}.{}.{}时 录播⭐】先行版'.format(record_info.get('month'),record_info.get('day'), record_info.get('hour')),
                tid=17,
                tag=",".join(["少年Pi", "API", "api", "少年pi"]),
                desc='''⭐少年Pi⭐{}.{}.{} 直播，单推地址：https://live.bilibili.com/92613
如果脚本不出bug的话，应该每天都会在这里滚动更新API当日录播的先行版。
仅供先行观看使用，正式版还请移步@少年Pi的奇妙录播。正式版发布后这里的内容随时作废。

（还在为录播迟迟没有更新而烦恼么！快来使用我的录播机，快就是快！ https://github.com/qqyuanxinqq/blive_Recorder）
'''.format(record_info.get('year'), record_info.get('month'),record_info.get('day')),
                thread_pool_workers=10,
                max_retry = 10,
                video_list_json = record_info.get('filename'),
                bvid="BV1TY411c7mN",
                submit_mode = 2
                ))
    else:
        raise Exception("Upload configuration missing for up_name %s"%record_info["up_name"])
    
    
    return configuration
    
def uploader_prepare(login_token_file, username: str = "username", password: str = "username"):
    uploader = BilibiliUploader()
    try:
        uploader.login_by_access_token_file(login_token_file)
        print("Successful! Logged in by token.")
    except Exception as e:
        logging.exception(e)
        print("Error with uploader.login_by_access_token_file")
        print(e)
        print("Try username/password login")
        rtncode = uploader.login(username, password)            #-449 error because of VPN required
        
        if rtncode != 0:
            raise Exception("username/password login fail")
        else:
            uploader.save_login_data(file_name=login_token_file)
    return uploader

def parts_prepare(record_info):
    # 处理视频文件
    directory = record_info.get('directory')
    parts = []
    file_list=record_info.get('videolist')
    for item in file_list:
        parts.append(VideoPart(
            path=os.path.join(directory, item),
            title = item.split('.')[0]
        ))
    return parts

def upload(record_info_json):
    with FileLock(record_info_json + '.lock'):
        with open(record_info_json, 'r') as f:
            record_info = json.load(f)

    if 'Status' not in record_info:
        print("Live status is not checked!")
        
    config = config_gen(record_info)
    try:
        login_token_file = os.path.join(record_info.get('directory'),"upload_log","bililogin.json")
        
        uploader = uploader_prepare(login_token_file, config.get("username"), config.get("password"))
        parts = parts_prepare(record_info)
        
        avid, bvid = uploader.replace_or_new(parts=parts, **config["upload_args"])
        print("Done! All video parts uploaded! Avid:{}, Bvid: {}".format(avid, bvid), flush = True)
    except Exception as e:
        logging.exception(e)
        print(e)
        logging.exception(e)
        print("Upload failed")
