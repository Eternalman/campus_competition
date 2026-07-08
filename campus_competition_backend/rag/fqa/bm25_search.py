"""
BM25 检索工作流：

1. 初始化连接
    1.初始化 Django ORM
    2.初始化 Django Cache

2. 加载数据并构建BM25检索器
    1.从mysql中读取所有问题
    2.对原始问题 进行分词
    3.构建bm25检索器

3. 查询问题主流程
    1.  判断query是否是 非空字符串
    2.  先查cache中是否有一样的问题
    3.  对query分词
    4.  用bm25计算query和所有问题的相似度
    5.  对相似度分数进行softmax归一化
    6.  取最大相似度分数，包括 原始分数 和 归一化分数
    7.  根据索引找到对应的原始问题
    8.  双重阈值判断。包括 相对阈值0.85 和 绝对阈值10.0
    9.  查看cache中是否有该问题的答案
    10. 查看mysql中是否有该问题的答案
    11. 返回答案，并写入cache
"""

# 导入 BM25 算法
from rank_bm25 import BM25Okapi
# 导入数值计算库
import numpy as np
# 导入文本预处理
from rag.fqa.preprocess import preprocess_text
# 导入日志
import logging
logger = logging.getLogger(__name__)

from rag.models import FqaEntry
from django.core.cache import cache

# 默认阈值常量（避免可变默认参数问题）
DEFAULT_THRESHOLD = (0.85, 10.0)

class BM25Search:
    # 1.初始化
    def __init__(self):
        # 1.初始化日志
        self.logger = logger
        # 2.初始化 bm25 模型
        self.bm25 = None
        # 3.初始化 原始问题列表（未分词，用 tuple 存储以节省内存）
        self.origin_questions: tuple[str, ...] = ()
        # 4.加载数据并构建BM25检索器
        self._load_data()

    # 2.加载数据并构建BM25检索器，mysql -> bm25
    def _load_data(self):
        """
        实现FQA 的加载数据 + 构建BM25检索器
        1.从mysql中读取所有问题
        2.对原始问题 进行分词
        3.构建bm25检索器
        :return: None
        """

        self.logger.info("系统第一次启动，正在加载数据...")
        # 1.从mysql中读取所有问题
        origin_questions = list(FqaEntry.objects.values_list('question', flat=True))
        if not origin_questions:
            self.logger.error("mysql中没有问题数据")
            raise ValueError("mysql中没有问题数据，BM25检索器无法构建")

        self.logger.info(f"从mysql中获取了问题，问题数量：{len(origin_questions)}")

        # 2.对原始问题进行分词（分词结果仅用于构建BM25模型，不保存为实例变量）
        questions = [preprocess_text(question) for question in origin_questions]

        # 3.构建bm25检索器（BM25Okapi 内部会保存语料库副本，无需额外存储分词结果）
        self.bm25 = BM25Okapi(questions)
        self.origin_questions = tuple(origin_questions)
        # 分词后的 questions 列表在此处不再需要，由垃圾回收释放，节省内存
        del questions
        self.logger.info("BM25模型构建成功")

    # 3.BM25检索主流程，query -> answer
    def search(self, query: str, threshold=DEFAULT_THRESHOLD):
        """
        实现 FQA 检索：用户输入一个query，进行bm25相似度检索，返回相似度超过双重阈值的问题对应的答案
        1.  判断query是否是 非空字符串
        2.  先查cache中是否有一样的问题
        3.  对query分词
        4.  用bm25计算query和所有问题的相似度
        5.  对相似度分数进行softmax归一化
        6.  取最大相似度分数，包括 原始分数 和 归一化分数
        7.  根据索引找到对应的原始问题
        8.  双重阈值判断。包括 相对阈值0.85 和 绝对阈值10.0
        9.  查看cache中是否有该问题的答案
        10. 查看mysql中是否有该问题的答案
        11. 返回答案，并写入cache
        :param query: 用户输入问题
        :param threshold: 阈值，包含相对阈值和绝对阈值（默认 (0.85, 10.0)）
        :return: (answer, is_rag): (答案, 是否需要调用RAG系统)
        """

        # 0. 检查BM25模型是否已初始化
        if self.bm25 is None:
            self.logger.error("BM25模型未初始化，无法执行查询")
            raise ValueError("BM25模型未初始化，无法执行查询")

        # 1. 判断query是否是 非空字符串
        if not isinstance(query, str) or not query.strip():
            self.logger.info(f"用户输入的query非法: {query}")
            # query非法，不需要进入RAG系统
            return None, False


        # 2. 先查cache中是否有一样的问题
        answer = cache.get(f"answer:{query}")
        if answer:
            self.logger.info(f"在cache中找到了一样问题: {query}")
            # 在cache中找到了一样的问题对应的答案，不需要进入RAG系统
            return answer, False

        # 2.1. 再查 self.origin_questions 中有没有一样的问题
        if query in self.origin_questions:
            self.logger.info(f"在 origin_questions中找到了一样问题: {query}，mysql找到答案")
            # 在self.origin_questions中找到了一样的问题对应的答案，不需要进入RAG系统
            answer = FqaEntry.objects.filter(question=query).values_list('answer', flat=True).first()
            if answer:
                # 回写缓存，下次同样问题直接从 Redis 命中
                cache.set(f"answer:{query}", answer, timeout=86400)
            return answer, False

        # 3. 对query分词
        query_tokens = preprocess_text(query)

        # 4. 用bm25计算query和所有问题的相似度
        scores = self.bm25.get_scores(query_tokens)



        # 5. 对相似度分数进行softmax归一化
        scores_softmax = self._soft_max(scores)



        # 6. 取最大相似度分数，包括 原始分数 和 归一化分数
        max_index = np.argmax(scores) # 获取最大值的索引
        max_score = scores[max_index] # 最大分数
        max_score_softmax = scores_softmax[max_index] # 最大归一化分数
        self.logger.info(f"最大相似度分数: 原始分数：{max_score}, 归一化分数: {max_score_softmax}")

        # 7. 根据索引找到对应的原始问题
        origin_question = self.origin_questions[max_index]
        self.logger.info(f"最相似问题: {origin_question}")

        # 8. 双重阈值判断。包括 相对阈值0.85 和 绝对阈值10.0
        if max_score_softmax > threshold[0] and max_score > threshold[1]:

            # 9. 查看cache中是否有该问题的答案
            answer = cache.get(f"answer:{origin_question}")

            if answer:
                self.logger.info(f"在cache中找到了答案")
                # 在cache中找到了相似度最高的问题的答案，不需要进入RAG系统
                return answer, False
            # self.logger.info(f"在cache中未找到答案")

            # 10. 查看mysql中是否有该问题的答案
            answer = FqaEntry.objects.filter(question=origin_question).values_list('answer', flat=True).first()
            if answer:
                self.logger.info(f"在mysql中找到了答案")
                # 11.返回答案，并回写答案到cache
                cache.set(f"answer:{origin_question}", answer, timeout=86400)
                # 在mysql中找到了相似度最高的问题的答案，不需要进入RAG系统
                return answer, False
            else:
                self.logger.info(f"在mysql中未找到答案")
                # 在mysql中未找到相似度最高问题的答案，需要进入RAG系统
                raise ValueError("在mysql中未找到答案")

        # 如果最大相似度分数未超过阈值，则需要进入RAG系统
        return None, True

    def _soft_max(self, scores):
        # 1.指数运算前减去最大值，避免数值溢出
        exp_scores = np.exp(scores - np.max(scores))
        # 2.归一化
        return exp_scores / np.sum(exp_scores)

# 主程序
if __name__ == '__main__':
    bm25_search = BM25Search()
    answer, is_rag = bm25_search.search("如何在 Ubunt 创建pycharm快捷方式？", threshold=(0.85, 18.0))
    print(f"答案: {answer}, 是否调用RAG系统: {is_rag}")
