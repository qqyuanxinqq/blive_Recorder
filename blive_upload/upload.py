from bilibiliuploader.bilibiliuploader import BilibiliUploader
from bilibiliuploader.core import VideoPart
import os,sys
import json

def upload(record_info):
    uploader = BilibiliUploader()
        
    directory = record_info.get('directory')
    login_token_file = os.path.join(directory,"upload_log", "bililogin.json")
    
    try:
        uploader.login_by_access_token_file(login_token_file)
    except Exception as e:
        print("Error with uploader.login_by_access_token_file")
        print(e)
        print("Try username/password login")
        uploader.login("username", "password")            #-449 error because of VPN required
        uploader.save_login_data(file_name=login_token_file)

    # 处理视频文件
    parts = []
    file_list=record_info.get('videolist')
    for item in file_list:
        parts.append(VideoPart(
            path=os.path.join(directory, item),
            title = item.split('.')[0]
        ))

    
    # 上传
    avid, bvid = uploader.upload(
        parts=parts,
        copyright=1,
        title='【⭐烤鱼子{}.{}录播⭐】摸了摸了'.format(record_info.get('month'),record_info.get('day')),
        tid=17,
        tag=",".join(["烤鱼", "烤鱼子", "录播", "烤鱼子Official"]),
        desc='''⭐烤鱼子Official⭐{}.{}.{} 直播，单推地址：https://live.bilibili.com/22259479
粉丝群：烤鱼盖浇饭研究协会：784611303，欢迎来摸鱼

本视频系自动上传，欢迎各位在评论区留下游戏内容、分P等相关信息'''.format(record_info.get('year'), record_info.get('month'),record_info.get('day')),
        thread_pool_workers=10,
        max_retry = 10,
        video_list_json = record_info.get('filename')
    )
    
    return avid, bvid
    

if __name__ == '__main__':
    lst = sys.argv
    with open(lst[1], 'r') as f:
        record_info = json.load(f)

    if 'Status' not in record_info:
        print("Live status is not checked!")

    avid, bvid = upload(record_info)
    print("Done! All video parts uploaded! Avid:{}, Bvid: {}".format(avid, bvid))
    

    
    
