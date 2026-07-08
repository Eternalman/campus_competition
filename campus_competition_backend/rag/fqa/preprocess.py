"""
文本预处理的流程：
1. 英文统一转小写
2. 把句子进行分词

什么时候调用：
1. 从MySQL中读取问题，进行分词，并写入分词后的问题 到redis，同时给bm25算法使用
2. 用户提交query进行查询，首先进行分词
"""
import jieba
# 导入日志
import logging
logger = logging.getLogger(__name__)

def preprocess_text(text):
    # 预处理文本
    logger.debug("开始预处理文本: {}".format(text))
    try:
        # 分词并转换为小写
        return jieba.lcut(text.lower())
    except AttributeError as e:
        # 记录预处理失败
        logger.error(f"文本预处理失败: {e}")
        # 返回空列表
        return []


if __name__ == '__main__':
    t= '我是NAME:wqj\n他们都叫我帅哥'
    txt=preprocess_text(t)
    print(t)
    print(txt)
