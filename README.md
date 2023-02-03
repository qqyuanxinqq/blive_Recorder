# blive_Recorder 

用于B站(Bilibili)的，全自动录制（含弹幕）、自动投稿命令行工具。**适用于Windows 和 linux。**
**适用于：NAS、服务器直播监控、录制及自动投稿**

- 后台24小时监视直播间，自动启用录制和投稿
- 无ffmepg依赖。内置FLV MetaData修复功能，修复录制文件不能跳转，时长显示错误等问题
- 根据实时弹幕自动生成视频文件对应的ass字幕文件，保留直播间原有弹幕样式
- 支持多P上传。支持单一视频的多线程上传。
- 录制上传同步进行，下播前就能发布录播，再长的直播也能结束后半小时内全部上传。快就是快！
- 在已有ffmpeg配置的情况下，支持将直播弹幕内压至录制视频。
## 用法
### 配置录制
对于每个需要录制的直播间，请在`config.json`文件中分别建立对应的配置段落，可参考自带的示例`config.json`。其中`"_default"`为默认全局配置，具体直播间的参数将覆盖`"_default"`中的配置。具体详细描述如下：
- `Enabled_recorder `**（仅用于"_default"全局）**: 启用录制的直播间列表。该列表为空时，启动所有存在配置的录制。不为空时，仅自动启用位于列表中的配置。
- `Database `**（仅用于"_default"全局）**: 启用数据库连接（目前仅支持sqlite）。设置为空字符串时不启用数据库连接。
- `Upload_configuration` **（仅用于"_default"全局）**: 开启自动上传时，上传所需的配置文件位置。
- `name`: 直播间或up主昵称（可任取），该名称会出现在所有相关文件中。**请确保该名称与该段配置对象名称相同。**
- `room_id`: 直播间ID。可在浏览器的直播间地址中获得。 
- `divide_video`: 视频文件分P方法以及对应参数。如`["size", 1.5]`(按视频大小分P，参数单位为gb), `["duration", 3600]`(按视频长度分P，参数单位为秒), `["rounding", 3600]`(对视频中止时间凑整点分P，参数单位为秒，此处`3600`即为整点分P)
- `upload`: 是否启用自动上传。1为启用，0为不使用。上传的配置方法另作介绍。
- `flvtag_update`: 是否启用flv标签修复。1为启用，0为不使用。
- `path`: 视频文件保存路径。视频，字幕，及其他录制信息将保存在该文件夹下的，你命名的_name子文件夹下。目前仅支持相对路径。
- `storage_stg`:

### 开启录制
- **单一任务，指定直播间**
```bash
#UP_NAME 为配置文件中对应段落名，也即_name字段内容）
$ python3 main.py UP_NAME

#Linux后台运行 (自行日志文件的输出请自行重定向或编辑bash脚本)
$ nohup python3 main.py UP_NAME & 
```
- **多任务模式，同时监控、录制多个直播间**
```bash
# 任务内容见配置文件中的Enabled_recorder字段
$ python3 main.py
```
```python
# 通过manage.py中的函数对任务内容进行管理
import manage
manage.add_task("kaofish")
```

### 配置上传
Todo
### 手动执行上传
上传所需的配置文件为`blive_upload`文件夹下的`cfg_upload.py`文件中的`cfg_gen`函数。其中`up_name`应与配置文件的文件名和描述相同。

对Python不了解的同学请按"exmaple"示例填写。
对Python有所了解的同学可参照"kaofish"填写，使用自定义的格式化字符串。

**由于B站更登录接口，使用帐号密码直接登录可能存在一定的问题，详见（附临时解决办法）：**
https://github.com/FortuneDayssss/BilibiliUploader/issues/41

## 今后计划
近期有空都会试着更新，不过个人能力很有限，有些实现可能也比较奇怪，希望大佬们多指教。

- Different upload mode, e.g. appending;
- 仅弹幕录制，Recorder基本类，Live_info serialization;  Optimize upload config format
- 通过与内置SQLite数据库的交互，记录直播、分P、弹幕信息，并给出通用接口
- ✓ 不同的分P条件 （固定时长分P, 整点分P，固定大小分P）
- 保存目录的绝对地址
- 对正在写入的视频实现上传，延后flvmeta的调用
- 根据弹幕文件做点分析？
- Reorgnize the class in record.py, to meet LoD. 
- Reorgnize the class in record.py, to meet DIP. 

## 参考及感谢

- [loveinshare/bilibili-stream-download](https://github.com/loveinshare/bilibili-stream-download) 最初版直播间API
- [FortuneDayssss/BilibiliUploader](https://github.com/FortuneDayssss/BilibiliUploader) 大佬的命令行上传工具！感谢！
- [FLVMeta - FLV Metadata Editor](https://flvmeta.com/) FLV标签修复工具
