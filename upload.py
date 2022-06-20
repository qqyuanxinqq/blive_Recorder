# from src.blive_upload import upload
import sys
from src.blive_upload import upload

if __name__ == '__main__':
    record_info_json = sys.argv[1]
    if len(sys.argv) == 2:
        upload(record_info_json)
    elif len(sys.argv) == 3:
        bvid = sys.argv[2]
        upload(record_info_json, bvid = bvid)
        
