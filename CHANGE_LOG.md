## 02/21/2023
Fixed the login issue associated with upload part.
Because old API no longer provides sid, sid is set to None. It looks like cookie (sid) is not required for upload. 

## 02/20/2023
Now support *.yaml configuration files that is more readable. 

## 12/11/2022
Now recorded video includes the live room title at at the start time.
Add options to set video title for upload

## 08/29/2022
Reorganize code related to video recording and processing. Now support burning Danmu(*.ass subtitle) into video files.  

## 06/26/2022
Change stream_url API to v2, hope the new stream_url format can fix stream download timeout.

## 06/26/2022
Add the support for FFmpeg recording.

## 06/21/2022
Add three different video splitting methods, by size, by duration, by time rounding.

## 05/30/2022
Add disk space management. This background thread will automatically check the usage of disk and delete the oldest video by default. 

## 05/27/2022
Fixed (hopefully) the "Database is locked" error. SQLite does not support concurrent writing, so frequency writing will lead to this error. (The overhead of this application should be low enough, but sometimes a connection will be held longer than necessary for unknown reason.) Now the DB writing frequnecy is decreased by buffering more danmu_DB entries in memory with a longer DB writing interval. 

## 05/24/2022
Now Live, Video, Danmu info will be recorded by the Sqlite through SQLAlchemy, which can be easily queried for further use.


## 05/09/2022
Add Flvmeta Windows binaries.


## 05/08/2022
Start to merge database into the recorder App. Now status of recorder App will be written into the SQLite, and the record in database can be used to control the recorder status!

## 05/06/2022
Some time ago, I reconstructed the websocket message handling process, but forget to commit. Now it adapts customized handlers, based on message type. Should be easier to extend message handling.

## 02/18/2022
Rewrite how the concurrent upload works. Previously one video file can only utilize one thread, now threads are created for each video file. 


### Lesson learnt:
Producer-Consumer model seems to not work well in this case, because Python threads cannot be closed explicitly, which makes it hard to terminate when error occurs for some chunks or after one video file is done. 

Maybe we can create upload workers used for all the time, in charge of all the post operations. 


