from threading import Lock


# 当前单进程内，问答、上传、删除和导出共用这一把锁。
graph_lock = Lock()