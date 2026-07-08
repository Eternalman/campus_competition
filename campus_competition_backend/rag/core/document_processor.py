"""
RAG系统的文档处理模块，实现功能：
1.定义文档加载器，根据不同的后缀名指定不同的文档加载器
2.文档加载：从指定文件夹加载多种类型文件并添加元数据
    1.遍历目录下的文件
    2.过滤文件类型，并加载文件
        2.1 根据文件类型来构造文档加载器。如果是 txt, csv,需要指定编码为 utf-8
        2.2 加载文件 并转为 Document
    3.给每个文档添加元数据：学科、路径、时间戳
3.文档分割：处理文档并进行两层切分，返回子块结果
    1.获取所有的Document
    2.初始化文档分割器
        2.1 对于markdown格式，使用MarkdownTextSplitter
        2.2 对于其他格式，使用自定义的 ChineseRecursiveTextSplitter
    3.把文件分割成多个子块
        3.1 把一个文档分割为多个父块chunk
        3.2 把每一个父块chunk 分割成多个子块sub_chunk
        3.3 给每个子块添加元数据，包括 parent_id, id, parent_content

"""

# core/document_processor.py
import os
# 文档加载器，把整个文档按照纯文本的形式加载成Document; 表格加载器，把表格数据转为Document对象
from langchain_community.document_loaders import TextLoader, CSVLoader, UnstructuredExcelLoader
# 文档加载器，把markdown格式的数据，提取文本内容，转成Document对象
from langchain_community.document_loaders.markdown import UnstructuredMarkdownLoader

# 支持markdown格式的切割（根据几级标题等）
from langchain_text_splitters import MarkdownTextSplitter

from datetime import datetime

# 中文递归分割器（主要因为中文和英文的标点符号不一样，所以我们不使用langchain自带的RecursiveTextSplitter）
from rag.splitters import ChineseRecursiveTextSplitter  # 分割器

# PDF、DOC、PPT、IMG 格式的数据都是我们自己写的
from rag.loaders import OCRPDFLoader, OCRDOCLoader, OCRPPTLoader, OCRIMGLoader  # 加载器
from django.conf import settings
config = settings.RAG_CONFIG
import logging
logger = logging.getLogger(__name__)

# 1.定义文档加载器，根据不同的后缀名指定不同的文档加载器
DOCUMENT_LOADERS = {
    # txt 使用TextLoader
    ".txt": TextLoader,  # txt  → TextLoader 类
    # PDF 使用 OCRPDFLoader
    ".pdf": OCRPDFLoader,  # PDF  → OCRPDFLoader 类
    # Word 使用 OCRDOCLoader
    ".docx": OCRDOCLoader,  # Word → OCRDOCLoader 类
    # PPT 使用 OCRPPTLoader
    ".ppt": OCRPPTLoader,
    # PPTX 使用 OCRPPTLoader
    ".pptx": OCRPPTLoader,
    # JPG 使用 OCRIMGLoader
    ".jpg": OCRIMGLoader,
    # PNG 使用 OCRIMGLoader
    ".png": OCRIMGLoader,
    # Markdown 使用 UnstructuredMarkdownLoader
    ".md": UnstructuredMarkdownLoader,
    # CSV 表格
    ".csv": CSVLoader,
    # Excel 表格（xlsx/xls）
    ".xlsx": UnstructuredExcelLoader,
    ".xls": UnstructuredExcelLoader
}


# 2.文档加载：从指定文件夹加载多种类型文件并添加元数据
def load_documents_from_directory(directory_path):
    """
    从指定文件夹加载多种类型文件并添加元数据, 处理文档并返回Document对象，用于后续进行文档分割
    :param directory_path: 要读取的路径，里面有RAG系统知识库的所有文档
    :return: 加载文档得到的Document对象的列表, list[Document]
    """
    # 定义一个空list,用于存放最终返回的结果
    documents = []

    # 获取所有支持的文件类型
    supported_extensions = DOCUMENT_LOADERS.keys()

    # 提取学科名称
    # D:\EduRAG_20260412\09-code_preview\00.project_code\integrated_qa_system\rag_qa\ai_data -> ai
    source = os.path.basename(directory_path).replace("_data", "")
    # 1.遍历目录下的文件
    # 作用：递归遍历指定目录下面的所有文件、文件名
    # root: 当前所在的目录
    # dirs: 当前目录下有哪些文件夹
    # files: 当前目录下有哪些文件
    for root, _, files in os.walk(directory_path):
        for file in files:
            # 2.过滤文件类型，并加载文件
            # 获取当前文件的完整路径
            file_path = os.path.join(root, file)
            # 获取当前文件的后缀，比如.txt, .pdf, .docx
            extension_name = os.path.splitext(file)[-1].lower()

            # 判断当前文件格式，DOCUMENT_LOADERS是否支持
            if extension_name in supported_extensions:
                try:
                    # 2.1 根据文件类型来构造文档加载器。如果是 txt, csv,需要指定编码为 utf-8
                    loader_class = DOCUMENT_LOADERS[
                        extension_name]  # 当 extension_name = ".pdf" 时，loader_class = OCRPDFLoader（类本身，不是实例）。

                    # 创建文档加载器对象,如果是 txt, csv,需要指定编码为 utf-8
                    if extension_name in [".txt", ".csv"]:
                        loader = loader_class(file_path,
                                              encoding="utf-8")  # 当文件是 a.txt 时，等价于：loader = TextLoader("a.txt", encoding="utf-8")

                    else:
                        loader = loader_class(file_path)  # 当文件是 c.pptx 时，等价于：loader = OCRPPTLoader("c.pptx")

                    # 这样写等价于
                    # if extension_name == ".txt":
                    #     loader = TextLoader(file_path, encoding="utf-8")
                    # elif extension_name == ".pdf":
                    #     loader = OCRPDFLoader(file_path)
                    # ...

                    # 2.2 加载文件 并转为 Document
                    # 返回 加载好的完整文档对象, list[Document对象]
                    # 返回的 list中，只有一个元素（Document对象），这里只有一个文件
                    # 调用加载器的 load() 方法，把文件内容提取出来，转为 LangChain 的 Document 对象列表。
                    loaded_docs = loader.load()
                    # print(f"len(loaded_docs): {len(loaded_docs)}")
                    # print(f"loaded_docs: {loaded_docs}")

                    # 3.给每个文档添加元数据：学科、路径、时间戳
                    # 为每个 Document 对象附加上下文信息。这些元数据在后续检索时会非常有用——比如用户问"AI 相关的知识"，系统可以根据 source 字段过滤。
                    for doc in loaded_docs:
                        doc.metadata["source"] = source  # 学科名，如 "ai"
                        doc.metadata["file_path"] = file_path  # 文件完整路径
                        doc.metadata["timestamp"] = datetime.now().isoformat()  # 加载时间
                        doc.metadata["extension"] = extension_name  # 文件后缀，如 ".pdf"

                    # 假设 loaded_docs = [Doc_A]
                    # 假设 documents 已有 [Doc_1, Doc_2]

                    # 用 append：  documents.append(loaded_docs)
                    # 结果：[Doc_1, Doc_2, [Doc_A]]  ← 嵌套了！多了一层 list

                    # 用 extend：  documents.extend(loaded_docs)
                    # 结果：[Doc_1, Doc_2, Doc_A]    ← 扁平展开，正确
                    documents.extend(loaded_docs)

                    logger.info(f"加载文件成功：{file_path}")

                except Exception as e:
                    logger.error(f"文件加载失败：{file_path}, error: {e}")
            else:
                logger.warning(f"不支持的文件类型：{file_path}")

    return documents


# 3.文档分割：处理文档并进行两层切分，返回子块结果
def process_documents(
        directory_path,
        parent_chunk_size=None,
        child_chunk_size=None,
        chunk_overlap=None
):
    """
    处理文档并进行两层切分，返回子块结果
    :param directory_path:  要处理的文档所在文件夹路径
    :param parent_chunk_size:   父块大小
    :param child_chunk_size:    子块大小
    :param chunk_overlap:   重叠字符数
    :return:    所有子块列表
    """
    if parent_chunk_size is None:
        parent_chunk_size = config['PARENT_CHUNK_SIZE']
    if child_chunk_size is None:
        child_chunk_size = config['CHILD_CHUNK_SIZE']
    if chunk_overlap is None:
        chunk_overlap = config['CHUNK_OVERLAP']

    # 1.获取所有的Document
    documents = load_documents_from_directory(directory_path)
    logger.info(f"加载文档成功，共 {len(documents)} 个文档")

    # 2.初始化文档分割器
    # 2.1 对于markdown格式，使用MarkdownTextSplitter
    markdown_parent_splitter = MarkdownTextSplitter(
        chunk_size=parent_chunk_size, chunk_overlap=chunk_overlap
    )
    markdown_child_splitter = MarkdownTextSplitter(
        chunk_size=child_chunk_size, chunk_overlap=chunk_overlap
    )

    # 2.2 对于其他格式，使用自定义的 ChineseRecursiveTextSplitter
    parent_splitter = ChineseRecursiveTextSplitter(
        chunk_size=parent_chunk_size, chunk_overlap=chunk_overlap,
    )
    child_splitter = ChineseRecursiveTextSplitter(
        chunk_size=child_chunk_size, chunk_overlap=chunk_overlap,
    )

    # 3.把文档分割成多个子块
    # 初始化空列表，用于存储所有子块
    child_chunks = []
    # 遍历原始文档，带上索引 i
    for i, doc in enumerate(documents):
        # 3.1 把一个文档分割为多个父块chunk
        # 获取文件扩展名，比如.md, .txt, .pdf, .docx
        # print(f"doc.metadata: {doc.metadata}")
        file_extension = doc.metadata.get("extension", ".pdf").lower()
        print(f"file_extension: {file_extension}")

        # 选择分割器
        is_markdown = file_extension in [".md", ".markdown"]  # 返回True or False
        parent_splitter_to_use = markdown_parent_splitter if is_markdown else parent_splitter
        child_splitter_to_use = markdown_child_splitter if is_markdown else child_splitter
        logger.info(
            f"正在处理文档：{doc.metadata.get('file_path', 'unknown')}, 分割器: {parent_splitter_to_use.__class__.__name__}")

        # 进行文档分割
        # 需要传入list格式, list[Document对象]
        parent_docs = parent_splitter_to_use.split_documents([doc])
        #             └────────┬────────┘    └──────┬──────┘ └─┬─┘
        #                  选好的切分器             方法名     传入一个列表，
        #                                                 里面只有1个Document

        logger.info(f"父块数量: {len(parent_docs)}")
        # print(f"parent_docs: {parent_docs}")

        # 3.2 把每一个父块chunk 分割成多个子块sub_chunk
        #  遍历父块，带上索引 j
        for j, parent_doc in enumerate(parent_docs):
            # 生成父块ID: doc_{i}_parent_{j}
            parent_id = f"doc_{i}_parent_{j}"
            print(parent_id)
            # 将 父块ID 添加到元数据
            parent_doc.metadata["parent_id"] = parent_id
            # 将父块 分割为子块
            sub_chunks = child_splitter_to_use.split_documents([parent_doc])

            # 3.3 给每个子块添加元数据，包括 parent_id, id, parent_content
            # 遍历子块，带上索引 k
            for k, sub_chunk in enumerate(sub_chunks):
                # 添加 父块ID 到子块元数据
                sub_chunk.metadata["parent_id"] = parent_id
                # 添加 父块内容 到子块元数据
                sub_chunk.metadata["parent_content"] = parent_doc.page_content
                # 添加 子块ID 到子块元数据,子块ID: {parent_id}_child_{k}
                sub_chunk.metadata["id"] = f"{parent_id}_child_{k}"
                # 添加子块 到 子块列表
                child_chunks.append(sub_chunk)
            print(child_chunks[0].metadata)
    # 记录子块数量
    logger.info(f"子块总数量: {len(child_chunks)}")
    return child_chunks


# 主程序
if __name__ == '__main__':
    # 1.文档加载
    # documents = load_documents_from_directory(directory_path=r"../ai_data")
    # print(documents)
    # 2.文档分块
    child_chunks = process_documents(
        os.path.join(str(settings.BASE_DIR), "rag", "data")
    )
    # print(child_chunks)
