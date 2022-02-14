from bilibiliuploader.bilibiliuploader import BilibiliUploader
from bilibiliuploader.core import VideoPart
import os,sys
import json

#Please change the title of this file into up_name.py
#请确保本文件名格式为up_name.py， 其中up_name应与配置文件一致

def upload(record_info):
    #Edit username and password here
    #此处输入上传账户的用户名和密码,请确保输入为字符串
    username = "xxxxx@xx.com"
    password = "secretnumbers"

    #Edit Information here, details in https://github.com/FortuneDayssss/BilibiliUploader
    #此处修改上传内容，标题，简介，tag等，详见https://github.com/FortuneDayssss/BilibiliUploader
    title='Title with no formatting'
    desc='''Some description
In multiple
Lines'''
    tag= "X,XX,XXX,XXXX" #Separated by comma

    # Donnot edit anything below if you are not familar with Python
    # 以下为python脚本内容，无关上传信息

    uploader = BilibiliUploader()
    directory = record_info.get('directory')
    login_token_file = os.path.join(directory,"upload_log", "bililogin.json")
    try:
        uploader.login_by_access_token_file(login_token_file)
        print("Successful! Logged in by token.")
    except Exception as e:
        print("Error with uploader.login_by_access_token_file")
        print(e)
        print("Try username/password login")
        rtncode = uploader.login(username, password)            #-449 error because of VPN required
        if rtncode != 0:
            raise Exception("username/password login fail")
        uploader.save_login_data(file_name=login_token_file)

    # 处理视频文件
    parts = []
    file_list=record_info.get('videolist')
    for item in file_list:
        parts.append(VideoPart(
            path=os.path.join(directory, item),
            title = item.split('.')[0]
        ))

    avid, bvid = uploader.upload(
        parts=parts,
        copyright=1,
        title=title,
        tid=17,
        tag=tag,
        desc=desc,
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
    

    
    
