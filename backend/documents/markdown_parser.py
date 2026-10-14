from typing import List
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from llm_models.embeddings_model import openai_embedding
from utils.log_utils import log
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document

from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter

class MarkdownParser:
    """
    专门负责markdown文件的解析和切片
    """
    def __init__(self):
        self.text_splitter = SemanticChunker(
            openai_embedding, 
            breakpoint_threshold_type="percentile",
            sentence_split_regex=r"(?<=[。！？])\s*|(?<=[.!?])\s+"
        )

    # def text_chunker(self, datas: List[Document]) -> List[Document]:
    #     new_docs = []
    #     for d in datas:
    #         #长度超过5000的datas[i]，则按照语义切割,小于的都原样保留
    #         if len(d.page_content) > 5000:  # 内容超出了阈值，则按照语义再切割
    #             new_docs.extend(self.text_splitter.split_documents([d]))
    #             continue
    #         new_docs.append(d)
    #     return new_docs
    def text_chunker(self, datas: List[Document]) -> List[Document]:
        byte_splitter = RecursiveCharacterTextSplitter(
            chunk_size=5500,
            chunk_overlap=300,
            length_function=lambda text: len(text.encode("utf-8")),
            separators=["\n\n", "\n", "。", "；", " ", ""],
        )

        new_docs = []
        for doc in datas:
            chunks = (
                self.text_splitter.split_documents([doc])
                if len(doc.page_content) > 5000
                else [doc]
            )
            for chunk in chunks:
                new_docs.extend(byte_splitter.split_documents([chunk]))

        return new_docs

   


    # def parse_markdown(self, md_file: str) -> List[Document]:
    #     loader = UnstructuredMarkdownLoader(
    #         file_path=md_file,
    #         mode='elements',
    #         strategy='fast'
    #     )
    #     docs = []
    #     for doc in loader.lazy_load():
    #         docs.append(doc)

    #     return docs
    #按元素切分md文档
    def parse_markdown(
        self, md_file: str, encoding: str = "utf-8"
    ) -> List[Document]:
        path = Path(md_file)
        text = path.read_text(encoding=encoding)

        # 按 Markdown 标题层级划分正文。
        headers = [
            ("#" * level, f"h{level}")
            for level in range(1, 7)
        ]
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers,
            strip_headers=True,
        )

        sections = splitter.split_text(text)
        docs = []

        for section in sections:
            body = section.page_content.strip()
            if not body:
                continue

            # 收集当前正文所属的标题路径。
            titles = [
                section.metadata[key]
                for _, key in headers
                if key in section.metadata
            ]
            title = " -> ".join(titles) if titles else path.stem

            docs.append(
                Document(
                    page_content=f"{title}\n\n{body}",
                    metadata={
                        "source": str(path),
                        "filename": path.name,
                        "filetype": "text/markdown",
                        "category": "content",
                        "title": title,
                        "category_depth": len(titles),
                    },
                )
            )

        return docs
    #原本的合并标题切分方法不合理 直接删掉了
    # def merge_title_content(self, datas: List[Document]) -> List[Document]:
    #     merged_data = []
    #     parent_dict = {}  # 是一个字典，保存所有的父document， key为当前父document的ID
    #     for document in datas:
    #         metadata = document.metadata
    #         if 'languages' in metadata:
    #             metadata.pop('languages')

    #         parent_id = metadata.get('parent_id', None)
    #         category = metadata.get('category', None)
    #         element_id = metadata.get('element_id', None)

    #         if category == 'NarrativeText' and parent_id is None:  # 是否为：内容document
    #             merged_data.append(document)
    #         if category == 'Title':
    #             document.metadata['title'] = document.page_content
    #             if parent_id in parent_dict:
    #                 document.page_content = parent_dict[parent_id].page_content + ' -> ' + document.page_content
    #             parent_dict[element_id] = document
    #         if category != 'Title' and parent_id:
    #             parent_dict[parent_id].page_content = parent_dict[parent_id].page_content + ' ' + document.page_content
    #             parent_dict[parent_id].metadata['category'] = 'content'

    #     # 处理字典
    #     if parent_dict is not None:
    #         merged_data.extend(parent_dict.values())

    #     return merged_data



     # def parse_markdown_to_documents(self, md_file: str, encoding='utf-8') -> List[Document]:
        #     documents = self.parse_markdown(md_file)
        #     log.info(f'文件解析后的docs长度: {len(documents)}')
    
        #     merged_documents = self.merge_title_content(documents)
    
        #     log.info(f'文件合并后的长度: {len(merged_documents)}')
    
        #     chunk_documents = self.text_chunker(merged_documents)
        #     log.info(f'语义切割后的长度: {len(chunk_documents)}')
        #     return chunk_documents
    
    def parse_markdown_to_documents(
            self, md_file: str, encoding: str = "utf-8"
    ) -> List[Document]:
        documents = self.parse_markdown(md_file, encoding=encoding)
        log.info(f"按Markdown标题分块后的长度: {len(documents)}")
    
        chunk_documents = self.text_chunker(documents)
        log.info(f"语义切割后的长度: {len(chunk_documents)}")
    
        return chunk_documents


if __name__ == '__main__':
    file_path = r'..\md\tech_report_0tfhhamx.md'
    parser = MarkdownParser()
    docs = parser.parse_markdown_to_documents(file_path)
    for item in docs:
        print(f"元数据: {item.metadata}")
        print(f"标题: {item.metadata.get('title', None)}")
        print(f"doc的内容: {item.page_content}\n")
        print("------" * 10)
