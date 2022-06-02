# from src.blive_upload import upload
import sys
from src.blive_upload import upload

if __name__ == '__main__':
    record_info_json = sys.argv[1]
    bvid = sys.argv[2]
    upload(record_info_json, bvid = bvid)
