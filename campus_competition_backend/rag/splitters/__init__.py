try:
    from rag.splitters.edu_chinese_recursive_text_splitter import ChineseRecursiveTextSplitter
except ImportError:
    ChineseRecursiveTextSplitter = None

try:
    from rag.splitters.edu_model_text_spliter import AliTextSplitter
except ImportError:
    AliTextSplitter = None
