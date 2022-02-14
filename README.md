# blive_Recorder 

适用于命令行调用的，用于录制和上传B站直播的工具。适用于linux。 windows尚不支持上传和flv修复功能。

## 亮点
- 根据实时弹幕自动生成视频文件对应的ass字幕文件，实现直播间原有弹幕样式
- 后台监视直播间，自动启用上传和录制
- 自动更新视频流的flv标签，修复录制文件不能跳转，时长显示错误等问题
- 支持多P上传
- 录制同时上传已完成的视频文件，小水管也能及时发出录播

## 用法
### 配置录制
对于每个需要录制的直播间，请在config文件夹下分别建立对应的配置文件UP_NAME.json，可参考自带的示例kaofish.json。详细描述如下：
- _name: 直播间或up主昵称，该名称会出现在所有相关文件中。**请确保该名称与配置文件本身名称相同。**
- _room_id: 直播间ID。可在浏览器的直播间地址中获得。 
- _div_size_gb: 视频文件分P大小，支持小数。
- _upload: 是否启用自动上传。1为启用，0为不使用。上传的配置方法另作介绍。
- flvtag_update: 是否启用flv标签修复。1为启用，0为不使用。Windows系统暂不支持。
- _path: 视频文件保存路径。视频，字幕，及其他录制信息将保存在该文件夹下的，你命名的UP_NAME子文件夹下。默认为当前文件目录下的Videos文件夹。目前仅支持相对路径。

### 开启录制
UP_NAME 为配置文件标题（不含“.json”）

命令行窗口运行
```
python3 main.py UP_NAME
```
后台运行
```
nohup python3 main.py UP_NAME & 
```
自行日志文件的输出请自行重定向或编辑bash脚本


### 配置上传
上传所需的配置文件为blive_upload文件夹下的UP_NAME.py文件。其中UP_NAME应与配置文件的文件名和描述相同。

对Python不了解的同学请按Exmaple.py示例填写。

对Python有所了解的同学可参照kaofish.py填写，使用自定义的格式化字符串。

## 今后计划
近期有空都会试着更新，不过个人能力很有限，有些实现可能也比较奇怪，希望大佬们多指教。

- Windows 命令行的支持和测试
- 不同的分P条件 （固定时长分P）
- 录制文件的绝对地址
- 根据弹幕文件做点分析？

## 参考及感谢

- [loveinshare/bilibili-stream-download](https://github.com/loveinshare/bilibili-stream-download) 最初版直播间API
- [FortuneDayssss/BilibiliUploader](https://github.com/FortuneDayssss/BilibiliUploader) 大佬的命令行上传工具！感谢！
- [FLVMeta - FLV Metadata Editor](https://flvmeta.com/) FLV标签修复工具
