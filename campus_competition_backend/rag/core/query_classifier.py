"""
查询分类模块：
    使用预训练 bert-base-chinese, 在二分类任务上微调，实现 通用知识 和 专业咨询 二分类
工作流：
    1.数据预处理
        加载JSON数据
        将查询文本和预测标签转化为模型输入
    2.构建数据集
        自定义DataSet
    3.加载预训练BERT模型
        预训练 bert-base-chinese
    4.模型微调
        设置配置参数，在训练集上训练
    5.模型评估
        在测试集上评估，生成分类报告和混淆矩阵
    6.模型预测
        加载训练好的模型，进行二分类预测

"""

# 导入标准库
import json
import os
import torch
# 导入日志
import sys
from django.conf import settings
config = settings.RAG_CONFIG
import logging
logger = logging.getLogger(__name__)
# 导入numpy
import numpy as np
# 导入 Transformers 库
from transformers import BertTokenizer, BertForSequenceClassification
# 模型训练和预测使用的工具
from transformers import Trainer, TrainingArguments

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# 0.全局配置
# 设置设备
DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "mps" if torch.mps.is_available() else "cpu"
)

# 超参数
BATCH_SIZE = 32
EPOCHS = 3
LR = 1e-5
WEIGHT_DECAY = 1e-3


class QueryClassifier(object):
    """
    0.初始化方法
    工作流：
        1.加载预训练BERT的tokenizer
        2.初始化微调后模型
        3.创建标签映射字典
        4.加载模型
    """
    def __init__(self, model_path='models/bert_query_classifier'):
        # 1.加载预训练BERT的tokenizer
        # 使用预训练模型，必须使用预训练的分词器，保证模型和分词器是匹配的
        self.pre_trained_model_path = os.path.join(str(config['MODELS_DIR']), 'bert-base-chinese')
        self.tokenizer = BertTokenizer.from_pretrained(self.pre_trained_model_path)

        # 2.初始化模型和设备
        self.model_path = model_path
        # 模型对象
        self.model = None
        # 设备
        self.device = DEVICE
        logger.info(f"使用设备: {self.device}")
        # 3.创建标签映射字典
        self.label_map = {"通用知识": 0, "专业咨询": 1}
        # 4.加载模型
        self.load_model()

    # 加载微调好的模型 或 预训练BERT
    def load_model(self):
        # 1.优先加载训练好的模型
        if os.path.exists(self.model_path):
            self.model = BertForSequenceClassification.from_pretrained(self.model_path)
            logger.info(f"模型加载成功：{self.model_path}")
        # 2.如果不存在训练好的模型，则加载预训练BERT
        else:
            # num_labels=2：实现二分类任务，对应输出线性层的输出维度为2
            self.model = BertForSequenceClassification.from_pretrained(
                self.pre_trained_model_path, num_labels=2
            )
            logger.info("加载预训练BERT模型")
        # 迁移模型到设备
        self.model.to(self.device)
        # print(self.model)

    # 保存 模型 和 词表
    def save_model(self):
        # 1. 保存模型
        os.makedirs(self.model_path, exist_ok=True)
        self.model.save_pretrained(self.model_path, safe_serialization=False)
        # 2. 保存词表。 token->id映射关系
        self.tokenizer.save_pretrained(self.model_path)
        logger.info(f"保存模型成功：{self.model_path}")

    """
    1.数据预处理，将查询文本和标签转化为模型输入
    工作流：
        1.对输入文本进行分词器编码
        2.返回编码结果和标签列表
    """
    def preprocess_data(self, texts, labels):
        # texts： [问题1,问题2,...问题n]
        # labels：[标签1,标签2,...标签n]
        # pt: pytorch的缩写。 tf: tensorflow
        encodings = self.tokenizer(
            texts, # 输入的文本
            truncation=True,  # 是否截断文本到 max_length
            padding=True, # 是否填充文本，按照当前批次最大长度填充
            max_length=128, # 最大长度
            return_tensors="pt", # 返回张量类型, pt: pytorch
        )

        # encodings 字典 -> input_ids , attention_mask , token_type_ids
        # label_map 字典 {'通用知识': 0}

        return encodings, [self.label_map[label] for label in labels]

    """
    2.构建数据集，用于模型训练
    工作流：
        1. 自定义DataSet类
            1 定义初始化方法
            2 定义__getitem__，根据索引获取对应的数据 {input_ids,attention_mask,token_type_ids,labels}
            3 定义__len__，获取数据集长度
        2. 返回Dataset对象
    """
    def create_dataset(self, encodings, labels):
        class MyDataset(torch.utils.data.Dataset):
            def __init__(self, encodings, labels):
                self.encodings = encodings
                self.labels = labels

            # 根据索引，获取对应的值
            def __getitem__(self, idx):
                # encodings: { 'input_ids': input_ids, 'attention_mask':attention_mask, 'token_type_ids'  }
                # input_ids: (batch_size, seq_len)
                # val[idx]： 第idx条数据的编码以后的id
                item = {key: val[idx] for key, val in self.encodings.items()}
                # 标签 转为 张量
                item["labels"] = torch.tensor(self.labels[idx], dtype=torch.int64)
                # item {"attention_mask":tensor, "input_ids":tensor, "token_type_ids":tensor,"labels":0或1}
                return item

            def __len__(self):
                return len(self.labels)

        return MyDataset(encodings, labels)

    """
    3.模型微调，在训练集上训练模型
    工作流：
        1. 数据预处理
            1.1 加载数据集
            1.2 把数据集划分成8:2的训练集和验证集
            1.3 把数据进行数值化
            1.4 构建Dataset
        2. 设置训练参数
        3. 初始化Trainer，传入参数、数据集、模型对象等
        4. 开始训练
        5. 保存模型
        6. 评估模型
    """
    def train_model(self, data_file='model_generic.json'):
        # 1.数据预处理
        # 保护性代码，确保训练的数据是存在的
        if not os.path.exists(data_file):
            logger.error(f"数据集文件 {data_file} 不存在")
            raise FileNotFoundError(f"数据集文件 {data_file} 不存在")

        # 打开文件作为f变量，最后退出的时候，自动调用close
        with open(data_file, "r", encoding="utf-8") as f:
            data = [json.loads(value) for value in f.readlines()]

        # 1.1 去重
        print("去重前数据集长度：", len(data))
        # 按 (query, label) 去重，保留首次出现样本（顺序稳定）
        seen = set()
        dedup_data = []
        for item in data:
            key = (item.get("query", "").strip(), item.get("label", "").strip())
            if key in seen:
                continue
            seen.add(key)
            dedup_data.append(item)

        data = dedup_data
        print("去重后数据集长度：", len(data))
        print(f"data: {data[:10]}")

        texts = [item["query"] for item in data]
        labels = [item["label"] for item in data]

        # 1.2 划分训练集和验证集（这里只是划分了训练集和验证集）
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            texts, labels, test_size=0.2, random_state=42, stratify=labels)

        # print(f"训练集长度：{len(train_texts)}, 验证集长度：{len(val_texts)}")

        # 1.3 数据预处理
        # preprocess_data ：传入文本，返回张量
        train_encodings, train_labels = self.preprocess_data(train_texts, train_labels)
        val_encodings, val_labels = self.preprocess_data(val_texts, val_labels)
        # print(f"train_encodings: {train_encodings}")
        # print(f"train_labels: {train_labels}")

        # 1.4 构建DataSet
        train_dataset = self.create_dataset(train_encodings, train_labels)
        val_dataset = self.create_dataset(val_encodings, val_labels)
        print(f"train_dataset: {train_dataset}")

        # 2. 设置训练参数
        training_args = TrainingArguments(
            output_dir="bert_results", # 模型和检查点保存的目录路径
            save_total_limit=1, # 最多保存1个检查点文件，超出时自动删除旧的
            num_train_epochs=EPOCHS, # 训练轮数
            per_device_train_batch_size=BATCH_SIZE, # 批次大小
            per_device_eval_batch_size=BATCH_SIZE,
            warmup_steps=500, # 学习率预热步数为500步，训练初期学习率从0逐渐增加到设定值
            weight_decay=WEIGHT_DECAY, # 权重衰减系数
            logging_dir="./bert_logs", # 日志文件保存的目录路径
            logging_steps=20, # 多少个训练步骤记录一次日志
            eval_strategy="epoch", # 评估策略为每个epoch结束后进行评估

            save_strategy="epoch", # 模型保存策略：开发阶段为每个epoch结束后保存，生产阶段为不保存模型

            load_best_model_at_end=True, # 训练结束后加载最佳模型而非最后一个模型
            metric_for_best_model="eval_loss", # 判断最佳模型的指标为评估损失

            fp16=False, # 禁用FP16混合精度训练，使用FP32精度, 兼容CPU和GPU
        )

        # 3.初始化 Trainer
        trainer = Trainer(
            # 传入要训练的模型实例
            model=self.model,
            # 传入上面定义的训练参数配置
            args=training_args,
            # 传入训练数据集
            train_dataset=train_dataset,
            # 传入验证数据集，用于训练过程中评估模型性能
            eval_dataset=val_dataset,
            # 传入计算评估指标的函数，用于在验证集上计算准确率等指标
            compute_metrics=self.compute_metrics
        )

        # 训练模型
        logger.info("开始训练 BERT 模型...")
        trainer.train()
        self.save_model()

        # 评估模型
        self.evaluate_model(val_texts, val_labels)

    def compute_metrics(self, eval_pred):
        """计算评估指标acc"""
        # logits：预测权重值 (batch_size,num_classes): [[-1.5, 2.0]]
        # labels: 真实值 (batch_size,): [[0]]
        logits, labels = eval_pred
        # softmax不会影响数据前后的单调性（logits里面最大值，转成softmax归一化以后得结果，还是最大值）
        # argmax需要的是索引， argmax得到的结果就是：1
        # prediction = 1 , label = 0
        # predictions: [batch_size] -> labels:[batch_size]
        predictions = np.argmax(logits, axis=-1)
        accuracy = (predictions == labels).mean()
        return {"accuracy": accuracy}

    """
    4.模型评估，输出分类报告和混淆矩阵
    工作流：
       1. 数据预处理
           1.1 对输入文本进行分词编码（截断/填充至128长度）
           1.2 创建包含编码和标签的tensor数据集
       2. 初始化预测工具
           2.1 创建Trainer实例加载当前模型
       3. 执行预测
           3.1 使用predict方法获取原始预测结果
           3.2 通过argmax解析预测标签，得到概率最大的预测值的标签id(0 ~ 1)
       4. 生成评估报告
           4.1 输出分类报告（含精确率/召回率/F1值）
           4.2 输出混淆矩阵
    """

    def evaluate_model(self, texts, labels):
        """评估模型性能"""
        # 对 texts 进行分词器编码，获得 encodings: {input_ids, attention_mask, token_type_ids}
        encodings = self.tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt"
        )
        dataset = self.create_dataset(encodings, labels)

        trainer = Trainer(model=self.model)
        predictions = trainer.predict(dataset)
        # predictions.predictions : (batch_size, 2)
        # np.softmax(predictions.predictions) ->  [-3.1, 2.7 ] /[ 0.3, 0.7 ]
        # argmax操作1维向量，所以我需要给它一个维度，它在哪个维度上去计算最大值 , array[-1]
        # predictions (batch,seq, num_classes=2)
        pred_labels = np.argmax(predictions.predictions, axis=-1)
        true_labels = labels  # 直接使用数字标签

        logger.info("分类报告:")
        logger.info(classification_report(
            true_labels,
            pred_labels,
            target_names=["通用知识", "专业咨询"]
        ))
        logger.info("混淆矩阵:")
        logger.info(confusion_matrix(true_labels, pred_labels))

    """
    5.模型预测
      比如： "Java学费一年多少钱"  -> "专业咨询"
    工作流：
        1. 加载模型, 并检查模型的状态
          1.1 验证模型是否已加载，未加载则记录错误并返回默认类别: 0->通用知识，让大模型处理query
        2. 输入数据处理
          2.1 对查询语句进行分词和编码（截断/填充至128长度）
          2.2 将编码数据移动到模型所在的设备
        3. 执行预测
          3.1 在无梯度模式下进行推理
          3.2 获取模型输出并解析预测结果（取logits最大值对应的类别）
        4. 结果映射
          4.1 将数字标签转换为对应的类别名称（0->通用知识，1->专业咨询）
    """
    def predict_category(self, query):
        # 检查模型是否加载
        if self.model is None:
            # 模型未加载，记录错误
            logger.error("模型未训练或加载")
            # 默认返回通用知识
            return "通用知识"
        # 对查询进行编码
        encoding = self.tokenizer(
            query,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt"
        )
        # 将编码移到指定设备
        encoding = {k: v.to(self.device) for k, v in encoding.items()}
        # 不计算梯度，进行预测
        with torch.no_grad():
            # 获取模型输出
            # {"attention_mask":attention_mask, "input_ids":input_ids,"token_type_ids": token_type_ids}
            outputs = self.model(**encoding)
            # 获取预测结果
            prediction = torch.argmax(outputs.logits, dim=1).item()
        # 根据预测结果返回类别
        return "专业咨询" if prediction == 1 else "通用知识"


if __name__ == '__main__':

    model = QueryClassifier(model_path=os.path.join(str(config['MODELS_DIR']), "bert_query_classifier"))
    path = os.path.join(str(settings.BASE_DIR), 'rag', 'data', 'model_generic.json')

    train_model = model.train_model(path)

    test_queries = [
        "AI学科的课程大纲是什么",
        "JAVA课程费用多少？",
        "5*9等于多少？",
        "AI培训有哪些老师？",
        "你是人吗",
        "蒙特卡罗树怎么用在风险投资的",
        "transformers有哪些常用的API",
        "大模型学费多少？",
        "大模型学什么？",
        "python大模型学科和智能应用开发有什么区别？"
    ]
    for query in test_queries:
        category = model.predict_category(query)
        print(f"查询: {query} -> 分类: {category}")
