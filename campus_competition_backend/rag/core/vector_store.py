"""
实现VectorStore
工作流：
    1.初始化 Milvus
    2.创建或加载 database 和 collection
    3.文档向量化 并写入 Milvus
    4.根据用户问题 进行混合检索(稠密向量+稀疏向量) + 重排/精排
    5.根据检索到的子块匹配父块，从子块列表中提取父块，并按父块内容去重。
注意：
    1.文档向量化：嵌入模型为bge-m3
    2.query向量化: 嵌入模型为bge-m3,同时获取 dense 和 sparse 向量，参考 https://bge-model.com/bge/bge_m3.html?utm_source=chatgpt.com
    3.两层排序策略：先粗排(混合检索) + 再精排(CrossEncoder,bge-reranker-large)，效果与效率的均衡
细节：
    路径中不要有中文

常见的面试题:
Q1：什么是向量数据库？为什么用 Milvus？
A：向量数据库用来存储向量，并按相似度快速检索。Milvus 是专门做大规模向量检索的工具，速度快，索引多，适合 RAG 场景。

Q2：为什么嵌入模型用 bge-m3？
A：因为 bge-m3 可以同时生成 dense 和 sparse 两种向量：
- dense：稠密向量，每一维都有值，负责语义相似；
- sparse：稀疏向量，只有少量非0值，负责关键词匹配；
一个模型同时支持两种检索，方便又实用。

Q3：嵌入模型和精排模型有什么区别？可以用同一个吗？
A：
- 嵌入模型：把文本变成向量，用来召回候选结果；
- 精排模型：对候选结果重新打分，选出最相关的内容。
一般不建议用同一个模型，因为两者任务不同。

Q4：dense 向量和 sparse 向量有什么区别？
A：
- dense（稠密向量）：每一维都有值，适合找"意思相近"的内容；
- sparse（稀疏向量）：只有少量维度非零，适合找"关键词相同"的内容。
比如"怎么登录失败"和"无法进入系统"，dense 可能都能找到；"Navicat 乱码"，sparse 更容易直接命中。

Q5：为什么要做混合检索？
A：因为用户问题有时看重语义，有时看重关键词。混合检索把 dense 和 sparse 结合起来，召回更全面，效果通常更稳。

Q6：IVF_FLAT 是什么？nlist 和 nprobe 是什么？
A：IVF_FLAT 是一种常见向量索引。它先把向量分成多个簇，再只在部分簇里搜索。
- nlist：簇的数量，越大越细；
- nprobe：查询时找多少个簇，越大越准但越慢。

Q7：为什么 sparse_index 常用 SPARSE_INVERTED_INDEX + IP？
A：因为 sparse 向量本质上是"词项-权重"，倒排索引适合做关键词检索，IP（内积）适合做权重匹配，所以这是主流做法。

Q8：WeightedRanker 和 RRF 有什么区别？怎么选？
A：
- WeightedRanker：按权重加权融合相似度结果，简单直接，但要人为设置权重；
- RRF：按相似度排名融合，不太受相似度数值大小影响，更稳定。
如果想设置权重，可以用 WeightedRanker；如果追求稳定，RRF 更常见。

Q9：为什么要先混合检索，再用 CrossEncoder 精排？直接精排不行吗？
A：不行，通常效率太低。先混合检索快速召回候选，再用 CrossEncoder 精排，能兼顾速度和准确率。

Q10：CrossEncoder 是什么？精排逻辑是什么？
A：CrossEncoder 会把 query 和 doc 一起输入模型，直接输出相关性分数。分数越高，说明这个文档越适合回答问题。它常用于"精排"。

Q11：hashlib 是什么？这里有什么用？
A：hashlib 是 Python 的哈希工具。这里用 MD5 给文本生成稳定 ID，方便 upsert。相同文本会得到相同 ID。

Q12：为什么要先连 default，再创建业务库？
A：如果业务库不存在，直接连接可能失败。先连 default 更稳定，再创建并切换到业务库，流程更安全。

Q13：这个检索流程一句话怎么说？
A：先把文档转成 dense+sparse 向量，并写入 Milvus；查询时做混合检索，再用 CrossEncoder 精排，最后返回最相关的父文档。

"""

# core/vector_store.py
# 导入 bge-m3 嵌入函数，用于生成文档和查询的向量表示
from milvus_model.hybrid import BGEM3EmbeddingFunction
# 导入 Milvus 相关类，用于操作向量数据库
from pymilvus import MilvusClient, DataType, AnnSearchRequest, WeightedRanker, RRFRanker
# 导入 Document 类，用于创建文档对象
from langchain_core.documents import Document
# 导入 CrossEncoder（交叉编码器），用于重排序(精排)
# 输入是一对文本 [query, doc]，模型让两段文本"同时参与注意力计算"，
# 直接输出一个相关性分数（分数越高，query 与 doc 越相关）。
from sentence_transformers import CrossEncoder
# 导入 hashlib 模块-哈希工具包，用于生成唯一 ID 的哈希值，任意长度的文本，都会生成一段固定长度的哈希字符串
import hashlib
# 导入 time 模块，用于生成时间戳
import time
from django.conf import settings
config = settings.RAG_CONFIG
import logging
logger = logging.getLogger(__name__)
import os
import torch

# 选择推理设备：cuda > cpu
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# Monkey-patch: FlagEmbedding 1.4.0 的 m3/runner.py 向 AutoModel.from_pretrained
# 传入 dtype= 参数名，但 transformers 4.44.2 期望 torch_dtype= 参数名。
# 此处修正参数名，避免 XLMRobertaModel.__init__() 收到意外的 dtype 关键字。
def _patch_flagembedding_dtype():
    try:
        from FlagEmbedding.finetune.embedder.encoder_only.m3 import runner as _m3_runner
        _original_get_model = _m3_runner.EncoderOnlyEmbedderM3Runner.get_model

        @staticmethod
        def _patched_get_model(
            model_name_or_path,
            trust_remote_code=False,
            colbert_dim=-1,
            cache_dir=None,
            torch_dtype=None,
        ):
            from transformers import AutoModel
            import os as _os
            from huggingface_hub import snapshot_download as _snapshot_download

            cache_folder = _os.getenv('HF_HUB_CACHE', None) if cache_dir is None else cache_dir
            if not _os.path.exists(model_name_or_path):
                model_name_or_path = _snapshot_download(
                    repo_id=model_name_or_path,
                    cache_dir=cache_folder,
                    ignore_patterns=['flax_model.msgpack', 'rust_model.ot', 'tf_model.h5']
                )

            model = AutoModel.from_pretrained(
                model_name_or_path,
                cache_dir=cache_folder,
                trust_remote_code=trust_remote_code,
                torch_dtype=torch_dtype,  # 修正：dtype → torch_dtype
            )
            colbert_linear = __import__('torch').nn.Linear(
                in_features=model.config.hidden_size,
                out_features=model.config.hidden_size if colbert_dim <= 0 else colbert_dim,
                bias=False,
            )
            sparse_linear = __import__('torch').nn.Linear(
                in_features=model.config.hidden_size, out_features=1, bias=False
            )
            return {
                'model': model,
                'colbert_linear': colbert_linear,
                'sparse_linear': sparse_linear,
            }

        _m3_runner.EncoderOnlyEmbedderM3Runner.get_model = _patched_get_model
        import logging
        logging.getLogger(__name__).info("FlagEmbedding dtype→torch_dtype monkey-patch applied.")
    except ImportError:
        pass


_patch_flagembedding_dtype()


# 1.定义类，实现向量存储与检索
class VectorStore:
    # 1.初始化 Milvus
    def __init__(
            self, collection_name=None, host=None,
            port=None, database=None,
    ):
        """
        初始化 Milvus
        1.构造 milvus连接参数
        2.创建 milvus客户端
        3.加载 embedding模型
        4.加载 rerank重排模型
        5.创建或加载 milvus集合

        :param collection_name: milvus集合名称
        :param host: milvus服务器地址
        :param port: milvus端口
        :param database: milvus数据库名称
        """
        # 1.构造 milvus连接参数（从 Django settings 获取默认值）
        self.collection_name = collection_name if collection_name is not None else config['MILVUS_COLLECTION_NAME']
        self.host = host if host is not None else config['MILVUS_HOST']
        self.port = port if port is not None else config['MILVUS_PORT']
        self.database = database if database is not None else config['MILVUS_DATABASE_NAME']
        self.logger = logger

        # 2.创建 milvus客户端
        # 先连接 milvus 默认数据库default, 避免目标数据库不存在而初始化失败
        self.client = MilvusClient(
            uri=f"http://{self.host}:{self.port}", db_name="default",
        )

        # 3.加载 embedding模型
        # bge-m3嵌入模型，同时生成 稠密向量 和 稀疏向量
        bge_m3_model_path = os.path.join(str(config['MODELS_DIR']), "bge-m3")
        self.embedding_function = BGEM3EmbeddingFunction(
            model_name_or_path=bge_m3_model_path,  # 传入模型名,自动下载；传入路径，直接加载
            use_fp16=False,  # 是否使用FP16精度；True表示使用FP16精度(精度低，速度快)，False表示使用FP32精度(精度高，速度慢)
            device=DEVICE,  # 推理设备
        )
        # 获取稠密向量维度，由嵌入模型决定
        self.dense_dim = self.embedding_function.dim['dense']

        # 4.加载 rerank重排模型
        # bge-reranker-large, 用于重排(精排)
        rerank_model_path = os.path.join(str(config['MODELS_DIR']), "bge-reranker-large")
        self.reranker = CrossEncoder(
            model_name=rerank_model_path,
            device=DEVICE,
        )

        # 5.创建或加载 milvus集合
        self._create_or_load_collection()

    # 2.创建或加载 database 和 collection
    def _create_or_load_collection(self):
        """
        创建或加载 database 和 collection
        1.创建并切换到指定database
        2.创建集合：如果集合不存在，创建字段与索引
        3.加载集合：如果集合已经存在
        :return: None
        """
        # 1.创建并切换到指定database
        if self.database not in self.client.list_databases():
            self.client.create_database(self.database)
            self.logger.info(f"创建数据库 {self.database} 成功")
        # 切换到指定database
        self.client.use_database(self.database)
        self.logger.info(f"切换到数据库 {self.database}")

        # 2.创建集合：
        # 判断集合是否已存在且有数据
        collection_exists = self.client.has_collection(self.collection_name)
        if collection_exists:
            # 检查已有集合中是否有数据
            stats = self.client.get_collection_stats(self.collection_name)
            row_count = int(stats.get("row_count", 0))
            if row_count > 0:
                # 集合已存在且有数据，直接复用，不删除
                self.logger.info(f"集合 {self.collection_name} 已存在且有 {row_count} 条数据，直接加载")
            else:
                # 集合存在但为空，删除后重建
                self.client.drop_collection(self.collection_name)
                self.logger.info(f"已删除空集合: {self.collection_name}")
                collection_exists = False

        # 如果集合不存在（或刚被删除），创建字段与索引
        if not collection_exists:
            # 1.创建schema
            schema = self.client.create_schema(
                auto_id=False,  # 是否自动生成id,False表示主键不自增
                enable_dynamic_field=True,  # 是否支持动态字段
            )
            # 2.设置field
            # 子块ID
            schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100)
            # 子块文本内容
            schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
            # 稠密向量，用于语义相似检索
            schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=self.dense_dim)
            # 稀疏向量，用于关键词匹配
            schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)
            # 父块ID
            schema.add_field(field_name="parent_id", datatype=DataType.VARCHAR, max_length=100)
            # 父块文本内容
            schema.add_field(field_name="parent_content", datatype=DataType.VARCHAR, max_length=65535)
            # 数据来源（学科名称），用于检索过滤
            schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=50)
            # 时间戳（字符串形式）
            schema.add_field(field_name="timestamp", datatype=DataType.VARCHAR, max_length=50)

            # 3.创建索引
            # 创建索引参数
            index_params = self.client.prepare_index_params()
            # 为稠密向量添加 IVF_FLAT索引，相似度度量方式为IP
            # nlist: 聚类中心的数量。nlist 越大，索引构建越慢，但检索精度通常越高；nlist 越小，检索速度越快，但可能牺牲精度。
            # nprobe: 查询时搜索的聚类中心数量。nprobe 越大，召回率越高，但检索耗时增加；nprobe 越小，检索速度越快，但可能漏掉相关结果。
            index_params.add_index(
                field_name="dense_vector",
                index_name="dense_index",
                index_type="IVF_FLAT",  # IVF_FLAT: 先聚类，再查询
                metric_type="IP",
                params={"nlist": 16}
            )

            # 为稀疏向量添加 SPARSE_INVERTED_INDEX索引，相似度度量方式为IP
            index_params.add_index(
                field_name="sparse_vector",
                index_name="sparse_index",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                params={"drop_ratio_build": 0.2}
                # drop_ratio_build: 稀疏向量索引构建时，对低贡献项的裁剪比例。drop_ratio_build 越小，索引构建越慢，但检索精度越高；drop_ratio_build 越大，索引构建越快，但可能丢失部分向量。
            )

            # 4.创建集合
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params
            )
            self.logger.info(f"创建集合 {self.collection_name} 成功")

        else:
            logger.info(f"集合 {self.collection_name} 已经存在")

        # 3.加载集合：如果集合已经存在
        self.client.load_collection(self.collection_name)
        self.logger.info(f"加载集合 {self.collection_name} 成功")

    # 3.文档向量化 并写入 Milvus
    def add_documents(self, documents, batch_size=30):
        """
        对文档进行向量化 并写入 Milvus
        1.分批处理文档
        2.批量生成向量(稠密/稀疏)
        3.组装数据
        4.upsert 写入 Milvus（同 ID 会覆盖）
        :param documents: 子块文档列表 list[Document]
        :param batch_size: 每批次处理文档的数量，避免一次性占用过多内存
        :return: None
        """
        # 1.分批处理文档
        total_docs = len(documents)
        logger.info(f"开始处理文档，文档总数：{total_docs}，批次大小：{batch_size}")

        # 遍历批次，通过获取 start_idx 和 end_idx 来获取当前批次的文档
        for start_idx in range(0, total_docs, batch_size):
            # 获取当前批次的结束索引
            end_idx = min(start_idx + batch_size, total_docs)

            # 获取当前批次的文档列表
            batch_docs = documents[start_idx:end_idx]
            logger.info(f"正在处理文档范围: {start_idx} - {end_idx - 1}，批次大小：{end_idx - start_idx}")

            # 提取当前批次的文本page_content
            texts = [doc.page_content for doc in batch_docs]

            # 2.批量生成向量(稠密/稀疏)
            try:
                # 使用嵌入模型获取文档向量, bge-m3模型 会同时获取稠密向量 和 稀疏向量
                embeddings = self.embedding_function(texts)
                # print(f"embeddings: {embeddings}")

                # 3.组装数据
                # dict列表，
                """
                list[
                    dict
                        {id:,text:,dense_vector:,sparse_vector:,parent_id:,parent_content:,source:,timestamp:}
                    ]
                """
                # 初始化数据列表
                data = []
                # 遍历当前批次的文档列表
                for i, child_doc in enumerate(batch_docs):
                    # 使用MD5生成子块文档ID
                    # MD5: 哈希算法，将任意长度的数据转换为固定长度字符串，32位十六进制字符串
                    text_hash = hashlib.md5(child_doc.page_content.encode('utf-8')).hexdigest()

                    # 获取稠密向量
                    dense_vector = embeddings["dense"][i].tolist()

                    # 获取稀疏向量，并构造 索引-权重 格式的dict
                    # {2:0.333,9:0.333,50:0.333}
                    sparse_row = embeddings["sparse"][i]

                    # 初始化稀疏向量字典
                    sparse_vector = {}

                    # 获取稀疏向量的非零值索引
                    indices = sparse_row.col

                    # 获取稀疏向量的非零值
                    values = sparse_row.data

                    # 将 索引 和 值 配对，构造稀疏向量字典
                    for idx, weight in zip(indices, values):
                        sparse_vector[int(idx)] = float(weight)

                    # 组装数据并添加到数据列表中
                    data.append({
                        "id": text_hash,
                        "text": child_doc.page_content,
                        "dense_vector": dense_vector,
                        "sparse_vector": sparse_vector,
                        "parent_id": child_doc.metadata["parent_id"],
                        "parent_content": child_doc.metadata["parent_content"],
                        "source": child_doc.metadata.get("source", "unknown"),
                        "timestamp": child_doc.metadata.get("timestamp", "unknown")
                    })

                # 4.upsert 写入 Milvus（同 ID 会覆盖）
                # 为什么 用upsert，不用insert: 相同ID要覆盖之前的数据，如果用insert就会出现相同ID的数据
                # 检查是否有数据，如果有则写入 milvus
                if data:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        data=data
                    )
                    self.logger.info(
                        f"写入文档(索引: {start_idx}-{end_idx - 1})到milvus集合 {self.collection_name}, 文档数量: {len(data)}")

            except Exception as e:
                self.logger.error(f"处理文档 (索引：{start_idx}-{end_idx - 1}) 时出错：{e}")
                continue

        self.logger.info(f"处理文档完成，总文档数：{total_docs}")

        # 刷新、释放、重新加载集合：
        # 1. flush：确保 upsert 的数据全部落盘
        # 2. release_collection：释放内存中旧的索引（该索引是在空集合上训练的）
        # 3. load_collection：重新加载集合，强制 IVF_FLAT 索引在有数据的情况下重新训练
        # 如果不做这一步，IVF_FLAT 索引是在空集合上初始化的，新插入的数据不在任何簇中，搜索会返回空结果
        self.client.flush(self.collection_name)
        self.client.release_collection(self.collection_name)
        self.client.load_collection(self.collection_name)
        self.logger.info(f"upsert 后 flush + release + reload 集合 {self.collection_name} 成功")

    # 4.根据用户问题 进行混合检索(稠密向量+稀疏向量) + 重排/精排
    def hybrid_search_with_rerank(self, query, top_k=None, source_filter=None):
        """
        根据用户问题 进行混合检索(粗排) + 重排(精排)。
        1.查询向量化：对 query 生成稠密/稀疏向量
        2.分别执行 dense/sparse 两路检索
        3.用 WeightedRanker/RRFRanker 融合结果(粗排)
        4.子块查父块，对父块合并去重
        5.用 reranker 做精排，返回最终检索的父块结果
        :param query: 用户问题
        :param top_k: 混合检索/粗排检索返回的候选数量
        :param source_filter: 可选来源过滤（比如指定学科）
        :return: 最终检索的父块结果
        """
        if top_k is None:
            top_k = config['RETRIEVAL_K']

        # 1.查询向量化：对 query 生成稠密/稀疏向量
        # 使用 写入Milvus 时的相同的嵌入模型bge-m3, 保证一样的文本的向量数值完全一致
        # bge-m3可以同时生成 稠密向量 和 稀疏向量
        # query -> bge-m3 -> query_embeddings: {dense:,sparse}
        query_embeddings = self.embedding_function([str(query)])

        # 获取稠密向量
        dense_query_vector = query_embeddings["dense"][0]

        # 获取稀疏向量
        sparse_row = query_embeddings["sparse"][0]

        # 初始化稀疏向量字典
        sparse_query_vector = {}
        # 获取稀疏向量的非零值索引
        indices = sparse_row.col
        # 获取稀疏向量的非零值
        values = sparse_row.data
        # 将 索引 和 值 撇对，构造稀疏向量字典
        for idx, weight in zip(indices, values):
            sparse_query_vector[int(idx)] = float(weight)

        # 可选来源过滤, 例如 source == 'ai'
        filter_expr = f"source == '{source_filter}'" if source_filter else None

        # 构建稠密检索请求：用于语义相似匹配
        dense_request = AnnSearchRequest(
            data=[dense_query_vector],
            anns_field="dense_vector",
            param={"metric_type": "IP", "params": {"nprobe": 4}},  # IP: 内积; nprobe: 查询最近的几个簇
            limit=top_k,
            expr=filter_expr
        )

        # 稀疏向量可能为空（bge-m3 对短文本/纯中文短语有时不产生稀疏特征），
        # 此时降级为纯稠密检索，避免 Milvus 报 "Sparse row data should not be empty"
        if not sparse_query_vector:
            self.logger.warning(f"稀疏向量为空，降级为纯稠密检索。query: {query[:50]}")
            search_kwargs = {
                "collection_name": self.collection_name,
                "data": [dense_query_vector],
                "anns_field": "dense_vector",
                "limit": top_k,
                "output_fields": ["id", "text", "parent_id", "parent_content", "source", "timestamp"],
                "search_params": {"metric_type": "IP", "params": {"nprobe": 4}},
            }
            # 新版 pymilvus MilvusClient.search() 用 filter 而非 expr
            if filter_expr:
                search_kwargs["filter"] = filter_expr
            results = self.client.search(**search_kwargs)[0]
        else:
            # 构建稀疏检索请求：用于关键词匹配
            sparse_request = AnnSearchRequest(
                data=[sparse_query_vector],
                anns_field="sparse_vector",
                param={"metric_type": "IP", "params": {}},  # IP: 内积
                limit=top_k,
                expr=filter_expr
            )

            # 用 RRFRanker 融合 dense + sparse 两路结果
            ranker = RRFRanker()

            # 查询结果为二维列表(n=1,limit=topK)
            results = self.client.hybrid_search(
                collection_name=self.collection_name,
                reqs=[dense_request, sparse_request],
                ranker=ranker,
                limit=top_k,
                output_fields=["id", "text", "parent_id", "parent_content", "source", "timestamp"]
            )[0]

        # 把子块结果转换为 Document
        res_child_chunks = [self._doc_from_hit(hit['entity']) for hit in results]

        # 4.子块查父块，对父块合并去重
        res_parent_docs = self._get_unique_parent_docs(res_child_chunks)

        """
        以上完成了粗排，下面开始 重排/精排
        """

        # 5.用 reranker 做精排，返回 config.CANDIDATE_M
        if res_parent_docs:
            # 如果只有一条，则直接返回
            if len(res_parent_docs) < 2:
                return res_parent_docs

            # 如果父块超过一个，需要进行重排序：基于query 和 父块内容 的匹配程度做重排序
            # 构造 (query, parent_content) 对，一起送入reranker模型做 重排/精排：计算query和parent_content的相关性，计算精度更高
            # 要求传入reranker的数据格式为 [[query, parent_content1],[query, parent_content2],[query, parent_content3],...]
            # 形状(n,2),n=参与检索的父块数量
            pairs = [[query, doc.page_content] for doc in res_parent_docs]

            # 送入reranker模型做 重排/精排
            scores = self.reranker.predict(pairs)  # 相似度分数

            # 排序，从大到小排序scores
            ranked_parent_docs = [doc for score, doc in sorted(zip(scores, res_parent_docs), reverse=True)]
            # 这里的重排序检索出的分数由大到小排序的 ranked_parent_docs, 其实就是检索上下文context

        else:
            # 直接返回空列表
            self.logger.info("无父块结果，返回空列表")
            return []
        # 返回CANDIDATE_M条父块结果
        return ranked_parent_docs[:config['CANDIDATE_M']]

    # 5. 把子块结果转换为 Document
    def _doc_from_hit(self, hit):
        """
        把 Milvus 命中结果（dict）转换为 Document 对象。
        :param hit: Milvus 命中结果
        :return:
        """
        return Document(
            page_content=hit['text'],
            metadata={
                # 'id': hit['id'],
                'source': hit['source'],
                'timestamp': hit['timestamp'],
                'parent_id': hit['parent_id'],
                'parent_content': hit['parent_content']
            }
        )

    # 6.根据子块匹配父块
    def _get_unique_parent_docs(self, child_chunks):
        """
        根据子块匹配父块，从子块列表中提取父块，并按父块内容去重。
        目的：避免同一父块因多个子块命中而重复返回。
        :param child_chunks: 子块列表
        :return: 去重后父块列表
        """
        parent_docs = set()
        # 返回值list[Document]
        unique_parent_docs = []

        for chunk in child_chunks:
            # 优先取 parent_content，缺失时退化为子块文本
            parent_content = chunk.metadata.get('parent_content', chunk.page_content)
            # 如果父块内容非空，且不重复
            if parent_content and parent_content not in parent_docs:
                # 构建一个父块对象，放到返回值集合中
                unique_parent_docs.append(
                    Document(
                        # 返回的 page_content 存放父块文本
                        page_content=parent_content,
                        metadata=chunk.metadata
                    )
                )
                parent_docs.add(parent_content)

        return unique_parent_docs


# 主程序
if __name__ == "__main__":
    import document_processor

    documents = document_processor.process_documents(
        os.path.join(str(settings.BASE_DIR), "rag", "data")
    )

    vector_store = VectorStore()
    vector_store.add_documents(documents=documents)
    result = vector_store.hybrid_search_with_rerank("大模型要学哪些知识？")
    print(len(result))
    print(result)
