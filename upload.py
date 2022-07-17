# from src.blive_upload import upload
import sys
from src.blive_upload import configured_upload

UPLOAD_CONFIGURATION = "upload_config.json"

if __name__ == '__main__':
    record_info_json = sys.argv[1]
    if len(sys.argv) == 2:
        configured_upload(record_info_json, UPLOAD_CONFIGURATION)
    elif len(sys.argv) == 3:
        bvid = sys.argv[2]
        configured_upload(record_info_json, UPLOAD_CONFIGURATION, bvid = bvid)
        
