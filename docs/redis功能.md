# 场景1：限流：
    登录按 IP 限流，问答按用户限流。
    固定窗口：限制一分钟内同一用户的请求次数√
    滑动窗口:限制当前节点为起点的一分钟内的请求次数
    token bucket：定时补token√ 
# 场景2：长期记忆的异步提取与入库的后台任务：
原本是fastAPI回答、保存聊天记录返回响应，进程内BackgroundTasks调用模型提取、筛选长期记忆、再保存到pgsql；
现在接入celery，用户正常问答时，API 在同一个事务中保存聊天消息和 outbox 待办记录。事务提交后，将任务投递到 Redis，独立的 Celery worker 调用模型、筛选候选记忆并保存到 PostgreSQL，任务投递失败时设置扫描程序补扫补投，执行异常由 Celery 重试，重复任务通过完成标记和行锁避免重复写入。
（函数注册成celery任务挂载到celery_app，fastAPI保存聊天消息后，用apply_async执行，该函数任务和参数会被加入redis队列，等待celery运行。
1）celeryworker未运行，apply_async()函数使得函数任务在redis排队，则任务会在celeryworker运行后执行；
2）celeryworker运行，但是任务重复排队：
    防止重复写入数据库的幂等操作如下：
    1：消息数据模型中加入完成标记字段，
    2：数据库用户、消息行锁，以及.with_for_update(...)锁住查询到的数据库行直至事务提交或回滚，
    3：with SessionLocal.begin()保证存储记忆和设置标记字段任务一起提交。实现重复任务时跳过避免重复写入。
    最后是写入pgsql的幂等（原本就有的）：行锁，双操作锁
    .with_for_update(of=ChatMessage)写前锁避免并发写，with SessionLocal.begin()保证写入消息和消息是否写入标记字段的修改在一个事务内部，保证原子性
3）celeryworker未运行且任务未排队：
    设置outbox代发送任务列表补投机制：
    新设计表模型保存代办数据，将保存代办数据和保存聊天函数融合（module/chat/router.py），消息添加发送情况字段，设计函数module/memory/task_patcher.py投递成功填写该字段否则该字段为空，设计scripts/dispatch_memory_task.py每十秒扫描未投递代办，补投，填写字段并调用任务函数通过执行celery的apply_async()函数发送到redis队列。
重试：Celery_app任务装饰器设置参数可以提取异常向外抛出，由 Celery 进行退避重试，可设置重试次数，退避基数，上限等。
幂等：以来源消息的 memory_extracted_at 字段判断是否已完成；结合数据库行锁，将记忆和完成标记在同一事务内提交，避免重复写入。
补投：投递失败时保留 outbox 待办，由独立扫描程序每 10 秒检查并重投；投递成功后更新 published_at。




# 场景3：多workder下的资源级并发控制：
会话级互斥：同一会话串行，不同会话并发。
文档级互斥：同一文档更新互斥，不同文档并发。
独立操作并发：上传、问答、导出不被同一把全局锁阻塞。
数据一致性：文档版本发布和导出快照，避免并发读取不完整数据。


原本：一个worker就是一个py进程，多个worker是多个py进程也就是内存，而每个内存中都有一个lock，所以多个worker可以同时处理一个会话。
现在：用redis保存所有worker的锁，以会话id作为锁标识，同一会话同一时间只允许一个worker执行，其他请求等待或返回正在处理。





# 场景4：检索缓存：缓存检索结果，文档更新后使缓存失效。   