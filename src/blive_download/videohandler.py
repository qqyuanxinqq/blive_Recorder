import datetime, time
import logging
import os
from typing import Callable, Tuple

import urllib3

from ..model.db import Video_DB

from .api import http
from .pyflvmeta import flvmeta_update


def flvmeta(video_db:Video_DB):
    filename = video_db.videoname
    print("==========Flvmeta============\n", filename, flush = True)
    rtn = flvmeta_update(filename)
    print("==========Flvmeta============\n", rtn, flush = True)


DURATION_THRESHOLD = 10
SIZE_THRESHOLD = 1000
RECORD_HEADER = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0 Iceweasel/38.2.1',
    'Referer': 'https://live.bilibili.com'
}

def record_source(url, file_name, check_func: Callable[[int, float], bool]) -> Tuple[int,int]:
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
                        headers=RECORD_HEADER,
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

def record_ffmpeg(url, file_name, check_func: Callable[[int, float], bool]) -> Tuple[int,int]:
    '''
    Record through FFmpeg. FFmpeg must be installed and accessible via the $PATH environment variable

    Return (status_code, size)
    '''
    import subprocess
    process = subprocess.run(['ffmpeg', '-version'], stdout= subprocess.PIPE)
    if process.returncode:
        raise FileNotFoundError("FFmpeg not found. FFmpeg must be installed and accessible via the $PATH environment variable")

    print(f'starting FFmpeg from:\n{url}\nto:\n{file_name}', datetime.datetime.now())
    
    import ffmpeg
    input = ffmpeg.input(url)
    output = ffmpeg.output(input, file_name, acodec='copy', vcodec='copy', loglevel = 'warning')
    # run: subprocess.Popen = output.run_async(cmd=['ffmpeg','-loglevel','quiet'])
    run: subprocess.Popen = output.run_async(pipe_stdout=subprocess.DEVNULL)
    size, duration = 0 ,0
    
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
        

def burn_subtitle(video_db:Video_DB, timeout = 600):
    """
    Use ffmpeg to burn substitles into the video. 
    Redirect video_db to the subtitled_video, and delete the unsubtitled one. 
    """

    assert video_db.subtitle_file
    assert os.path.isfile(video_db.subtitle_file)
    assert os.path.isfile(video_db.videoname)

    import subprocess
    process = subprocess.run(['ffmpeg', '-version'], stdout= subprocess.PIPE)
    if process.returncode:
        raise FileNotFoundError("FFmpeg not found. FFmpeg must be installed and accessible via the $PATH environment variable")

    subtitledVideo = ".".join(video_db.videoname.split(".")[:-1]) + "_subtitled.flv"
    print(f'starting FFmpeg embedding subtitle \n{video_db.subtitle_file}\nto:\n{video_db.videoname}\n and output to \n{subtitledVideo}', datetime.datetime.now())
    
    import ffmpeg
    run: subprocess.Popen = (ffmpeg.input(
        video_db.videoname,
        vcodec="h264_cuvid",  # GPU accelerated
        loglevel = "warning",
    )
        .filter("ass", video_db.subtitle_file)
        .output(
            subtitledVideo,
            vcodec="h264_nvenc",  # GPU accelerated
            acodec="copy",
            map="0:a",  # Map audio channel
            cq="30",  # Lower number means better quality and larger size
            flvflags = "add_keyframe_index"     #Used to facilitate seeking
        )
        # .overwrite_output()          #Overwrite output files without asking (ffmpeg -y option)
        .run_async()
    )

    #Check whether the size of output is changing.
    size = 0 
    delta_t = 10
    try:
        prev_size = 0
        while True:
            time.sleep(delta_t)
            size = 0 if not os.path.isfile(subtitledVideo) else os.path.getsize(subtitledVideo)

            if run.poll() is None:
                if size == prev_size:
                    timeout = timeout - delta_t
                    if timeout <= 0:
                        print("=============embed_subtitle not working somehow!==============")
                        break
            else:
                print("=============embed_subtitle terminated!==============")
                break
            prev_size = size
    finally:
        run.terminate()

    #Update video_db info
    time.sleep(10)
    rtncode = run.poll()
    if not os.path.isfile(subtitledVideo) or rtncode != 0:
        raise Exception(f"burn_subtitle failed, error code {rtncode}")
    else:
        os.remove(video_db.videoname)
        print(f"os.remove({video_db.videoname})")
        video_db.videoname = subtitledVideo
        video_db.size = os.path.getsize(subtitledVideo)
        # os.remove(video_db.subtitle_file)
        # video_db.subtitle_file = ""
