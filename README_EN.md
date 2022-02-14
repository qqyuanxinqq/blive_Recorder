# blive_Recorder 
Command Line Tool for Recording and uploading Bilibili Live
用于录制和上传B站直播的命令行工具, 适用于linux, windows尚不支持上传

## Feature
- Monitor the configured channel, automatically start recording and uploading 
- Fix FLV tags in recorded video stream, allowing seeking events

- Support multipart video upload
- Upload recorded parts while recording current stream, let you publish earlier

## How to use
### Configuration
The tool currently has no global configuration. For each channel, please configure the $UPNAME.json file in config folder. An example JSON file is included.

- _name: Nickname this channel, will appear in all related file name. Must be the same as the name of this JSON file.
- _room_id: Room id involved in the Live Room URL. 
- _div_size_gb: float number for maximum video part size.
- _upload: Enable(1) or disable(0) automatic upload. The configuration for upload will be mentioned in next section.
- flvtag_update: Enable(1) or disable(0) flv tag fix.
- _path: 


```
{
    "_name":"kaofish",
    "_room_id":"22259479",
    "_div_size_gb":"2",
    "_upload":1,
    "flvtag_update": 1,
    "_path":"Videos/",

    "token_file":"bililogin.json"
}

```

### Run
```
python3 main.py $UP_name
```

## Todo
1. Replace all print() into logging
2. Add different recording termination conditions
4. Total Danmu summar/analysis
5. Path setting

## Reference & Acknowledgements

- [loveinshare/bilibili-stream-download](https://github.com/loveinshare/bilibili-stream-download) Bilibili Live API
- [FortuneDayssss/BilibiliUploader](https://github.com/FortuneDayssss/BilibiliUploader) Command Line Tool for Upload
- [FLVMeta - FLV Metadata Editor](https://flvmeta.com/) Tool for Metadata injection
