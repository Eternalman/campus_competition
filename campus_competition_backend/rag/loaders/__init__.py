# 条件导入，OCR 可能依赖 rapidocr，允许优雅降级
try:
    from rag.loaders.edu_pdfloader import OCRPDFLoader
except ImportError:
    OCRPDFLoader = None

try:
    from rag.loaders.edu_docloader import OCRDOCLoader
except ImportError:
    OCRDOCLoader = None

try:
    from rag.loaders.edu_pptloader import OCRPPTLoader
except ImportError:
    OCRPPTLoader = None

try:
    from rag.loaders.edu_imgloader import OCRIMGLoader
except ImportError:
    OCRIMGLoader = None
