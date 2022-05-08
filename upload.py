from blive_upload import upload
import sys

if __name__ == '__main__':
    record_info_json = sys.argv[1]
    upload(record_info_json)