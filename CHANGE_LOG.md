## 02/18/2022
Rewrite how the concurrent upload works. Previously one video file can only utilize one thread, now threads are created for each video file. 

### Lesson learnt:
Producer-Consumer model seems to not work well in this case, because Python threads cannot be closed explicitly, which makes it hard to terminate when error occurs for some chunks or after one video file is done. 

Maybe we can create upload workers used for all the time, in charge of all the post operations. 