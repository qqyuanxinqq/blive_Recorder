import sys
from blive_download import Recorder
from blive_upload import upload

if __name__ == '__main__':
    # Get up_name from prompt
    up_name = sys.argv[1]
    # Up_name should be matched up with configuration file (i.e. kaofish for ./config/kaofish.json)
    recorder = Recorder(up_name)
    recorder.upload_func = upload
    recorder.recording()




            
