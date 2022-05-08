import os
import json
import logging
from filelock import FileLock
import logging

from .bilibiliuploader.bilibiliuploader import BilibiliUploader
from .bilibiliuploader.core import VideoPart


def cfg_gen(record_info, up_name = None) -> dict:
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

        本视频系自动上传，欢迎各位在评论区留下游戏内容、分P等相关信息'''.format(record_info.get('year'), record_info.get('month'),record_info.get('day')),
                thread_pool_workers=10,
                max_retry = 10,
                video_list_json = record_info.get('filename')))
    else:
        raise Exception("Upload configuration missing for up_name %s"%record_info["up_name"])
    
    return configuration


def _upload(record_info, upload_args : dict, username: str = "username", password: str = "username"):
    uploader = BilibiliUploader()

    directory = record_info.get('directory')
    login_token_file = os.path.join(directory,"upload_log", "bililogin.json")
    
    try:
        uploader.login_by_access_token_file(login_token_file)
        print("Successful! Logged in by token.")
    except Exception as e:
        logging.exception(e)
        print("Error with uploader.login_by_access_token_file")
        print(e)
        print("Try username/password login")
        
        #Edit username and password here
        #此处输入上传账户的用户名和密码， 替换"username", "password"字符
        rtncode = uploader.login(username, password)            #-449 error because of VPN required
        
        
        if rtncode != 0:
            raise Exception("username/password login fail")
        else:
            uploader.save_login_data(file_name=login_token_file)

    # 处理视频文件
    parts = []
    file_list=record_info.get('videolist')
    for item in file_list:
        parts.append(VideoPart(
            path=os.path.join(directory, item),
            title = item.split('.')[0]
        ))

    
    #Edit Information here, details in https://github.com/FortuneDayssss/BilibiliUploader
    #此处修改上传内容，标题，简介，tag等，详见https://github.com/FortuneDayssss/BilibiliUploader
    avid, bvid = uploader.upload(
        parts=parts,
        **upload_args
    )
    return avid, bvid
    
def upload(record_info_json):
    with FileLock(record_info_json + '.lock'):
        with open(record_info_json, 'r') as f:
            record_info = json.load(f)

    if 'Status' not in record_info:
        print("Live status is not checked!")
    config = cfg_gen(record_info)
    try:
        avid, bvid = _upload(record_info, **config)
        print("Done! All video parts uploaded! Avid:{}, Bvid: {}".format(avid, bvid), flush = True)
    except Exception as e:
        logging.exception(e)
        print(e)
        logging.exception(e)
        print("Upload failed")
