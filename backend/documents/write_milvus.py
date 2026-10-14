import multiprocessing
import os
from multiprocessing import Queue

from documents.markdown_parser import MarkdownParser
from documents.milvus_db import MilvusVectorSave
from utils.log_utils import log


# 采用分布式，多进程的方式把海量数据写入Milvus数据库
#batch_size = 20，表示累计至少 20 个文档块后发送。chunk列表的大小。
# Queue(maxsize=20)是batchsize的数量,是chunk列表的队列
def file_parser_process(dir_path: str, output_queue: Queue, batch_size: int = 20):
    """进程1：解析目录下所有md文件并分批放入队列"""
    log.info(f"解析进程开始扫描目录: {dir_path}")

    # 获取目录下所有.md文件
    md_files = [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if f.endswith('.md')
    ]

    if not md_files:
        log.warning("警告：未找到任何.md文件")
        output_queue.put(None)  # 发送终止信号
        return

    parser = MarkdownParser()
    doc_batch = []
    for file_path in md_files:
        try:
            docs = parser.parse_markdown_to_documents(file_path)
            if docs:
                doc_batch.extend(docs)

            # 达到批次大小时发送 到队列中
            if len(doc_batch) >= batch_size:
                output_queue.put(doc_batch.copy())
                doc_batch.clear()  # 清空当前缓冲区的所有批次数据
        except Exception as e:
            log.error(f"解析失败 {file_path}")
            output_queue.cancel_join_thread()
            raise

    # 发送剩余文档
    if doc_batch:
        output_queue.put(doc_batch)

    # 发送终止信号
    output_queue.put(None)
    log.info(f"解析完成，共处理{len(md_files)}个文件")


def milvus_writer_process(input_queue: Queue):
    """进程2：从队列读取并写入Milvus"""
    log.info("Milvus写入进程启动...")


    mv = MilvusVectorSave()
    mv.create_connection()
    total_count = 0
    while True:
        try:
            datas = input_queue.get()  # 阻塞的函数
            if datas is None:  # 收到了终止的信号
                break

            if isinstance(datas, list):
                mv.add_documents(datas)
                total_count += len(datas)
                log.info(f"累计已写入: {total_count} 个文档")
        except Exception as e:
            log.exception(f"写入数据失败 ！")
            raise

    log.info(f"写入进程结束，总计写入 {total_count} 个文档")


if __name__ == '__main__':
    # 配置参数
    md_dir = r'D:\1pyproject\rag0\md'
    # md_dir = r'D:\1pyproject\rag0\RAG_PROJECT\RAG_PROJECT\datas\batch_test_md'  # Markdown文件目录
    queue_maxsize = 20  # 队列最大容量（防止内存溢出）

    # 启动子进程前检查输入目录
    if not os.path.isdir(md_dir):
        raise NotADirectoryError(f"目录不存在: {md_dir}")

    md_files = [
        name
        for name in os.listdir(md_dir)
        if name.endswith(".md")
        and os.path.isfile(os.path.join(md_dir, name))
    ]

    if not md_files:
        raise ValueError(f"测试目录中没有 Markdown 文件: {md_dir}")

    print(f"本次待处理文件数: {len(md_files)}")

    mv = MilvusVectorSave()
    mv.create_collection()

    # 创建进程间通信队列
    docs_queue = Queue(maxsize=queue_maxsize)

    # 启动子进程
    parser_proc = multiprocessing.Process(
        target=file_parser_process,
        args=(md_dir, docs_queue)
    )
    writer_proc = multiprocessing.Process(
        target=milvus_writer_process,
        args=(docs_queue,)
    )

    # parser_proc.start()
    # writer_proc.start()

    # # 等待进程结束
    # parser_proc.join()
    # writer_proc.join()

    # print("系统提示：所有任务完成")

    processes = [parser_proc, writer_proc]

    try:
        for proc in processes:
            proc.start()

        while True:
            # 定期检查两个进程，避免一直等待其中一个。
            for proc in processes:
                if proc.pid is not None:
                    proc.join(timeout=0.2)

            failed = [
                proc
                for proc in processes
                if proc.exitcode is not None and proc.exitcode != 0
            ]#从 processes 里找出所有“已经结束，并且是异常结束”的子进程。

            if failed:
                details = ", ".join(
                    f"{proc.name}: exitcode={proc.exitcode}"
                    for proc in failed
                )
                raise RuntimeError(f"批量入库失败，子进程异常退出：{details}")

            if all(proc.exitcode == 0 for proc in processes):
                break

    finally:
        # 出错或按 Ctrl+C 时，停止仍在等待的子进程。
            for proc in processes:
                if proc.is_alive():
                    proc.terminate()

            for proc in processes:
                if proc.pid is not None:
                    proc.join()

            docs_queue.close()
            docs_queue.join_thread()

    print("系统提示：解析进程和写入进程均正常结束")