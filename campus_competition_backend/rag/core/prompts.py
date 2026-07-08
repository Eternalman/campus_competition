"""
管理 RAG系统的 提示词模板，包括 system prompt, user prompt

解释检索上下文retrival context 和 模型上下文LLM context 的区别:
    retrival context: 特指RAG系统中，检索向量库返回的内容
    LLM context: 输入给LLM的所有信息

"""


# core/prompts.py
# 导入 PromptTemplate 类，用于创建 Prompt 模板
from langchain_core.prompts import PromptTemplate

# 定义 RAGPrompts 类，用于管理所有 Prompt 模板
class RAGPrompts:
    """
    RAGPrompts 类用于管理所有 Prompt 模板。
    包含两类 Prompt：
    1. system_prompt：LLM API 调用时的 system role 消息，定义 LLM 的角色和行为准则
    2. 用户消息模板（PromptTemplate）：拼接 context/history/question 等变量后作为 user role 消息
    """

    # ======================== System Prompts ========================

    @staticmethod
    def rag_system_prompt():
        """RAG 检索模式的 system prompt：定义角色和回答风格，具体约束由 rag_prompt 控制"""
        return (
            "你是一名专业的校园赛事智能助手，面向参赛学生、评委和管理员。"
            "回答应准确、清晰、简洁，易于理解。"
            "仅基于提供的上下文回答，禁止使用自身知识。"
        )

    @staticmethod
    def general_system_prompt():
        """通用知识模式的 system prompt：允许使用自身知识直接回答"""
        return (
            "你是一名专业的校园赛事智能助手。"
            "请根据你的知识准确、清晰、简洁地回答用户问题。"
            # "如果你不确定答案，请如实说明。"
        )

    @staticmethod
    def strategy_system_prompt():
        """策略选择 和 优化query的 system prompt：严格执行 prompt 指令
        也可以区分 选择检索策略 和 优化query的 system_prompt
        """
        return "你是一个有用的助手，能够根据用户输入的Prompt严格执行并返回可靠的结果。"

    # ======================== User Message Templates ========================

    # 1. 定义 走RAG检索流程 的拼接Prompt的 Prompt 模板, 用于回答 专业咨询 的query
    @staticmethod
    def rag_prompt():
        return PromptTemplate(
            template="""
        你是一个智能助手，负责帮助用户回答校园赛事相关问题。请按照以下步骤处理：

        1. **分析问题和上下文**：
           - 仅基于提供的上下文回答，禁止使用自身知识。如果上下文中没有答案，直接回复"信息不足，无法回答，请联系人工客服，电话：{phone}。"。
           - 如果答案来源于检索到的文档，请在回答中明确说明，例如："根据提供的文档，……"。

        2. **评估对话历史**：
           - 检查对话历史是否与当前问题相关（例如，是否涉及相同的比赛、赛事规则或活动背景）。
           - 如果对话历史与问题相关，请结合历史信息生成更准确的回答。
           - 如果对话历史无关（例如，仅包含问候或不相关的内容），忽略历史，仅基于上下文和问题回答。

        3. **生成回答**：
           - 提供清晰、准确的回答，避免无关信息。
           - 如果上下文和历史消息均不足以回答问题，请回复："信息不足，无法回答，请联系人工客服，电话：{phone}。"

        **上下文**: {context}
        **对话历史**:
        {history}
        **问题**: {question}

        **回答**:
        """,
            input_variables=["context", "history", "question", "phone"],
        )

    # 2. 定义直接调用LLM的 拼接Prompt的 Prompt 模板，用于回答 通用知识 的query
    @staticmethod
    def general_prompt():
        return PromptTemplate(
            template="""
        你是一个智能助手，负责帮助用户回答问题。

        请根据你的知识直接回答用户的问题，回答应准确、清晰、简洁。
        如果你不确定答案，请如实说明。

        **对话历史**:
        {history}
        **问题**: {question}

        **回答**:
        """,
            input_variables=["history", "question"],
        )

    # 3. 定义 假设问题检索策略（HyDE） 的 Prompt 模板
    @staticmethod
    def hyde_prompt():
        #   创建并返回 PromptTemplate 对象
        return PromptTemplate(
            template="""
            用户想了解以下问题，请生成一个简短的假设答案：
            问题: {query}
            假设答案:
            """,
            #   定义输入变量
            input_variables=["query"],
        )

    # 4. 定义 子查询检索策略 的 Prompt 模板
    @staticmethod
    def subquery_prompt():
        #   创建并返回 PromptTemplate 对象
        return PromptTemplate(
            template="""
            将以下复杂查询分解为多个简单子查询，每行一个子查询：
            查询: {query}
            子查询:
            """,
            #   定义输入变量
            input_variables=["query"],
        )

    # 5. 定义 回溯问题检索策略 的 Prompt 模板
    @staticmethod
    def backtracking_prompt():
        #   创建并返回 PromptTemplate 对象
        return PromptTemplate(
            template="""
            将以下复杂查询简化为一个更简单的问题：
            查询: {query}
            简化问题:
            逻辑： 这个模板的作用是将用户提出的复杂问题简化/回溯为一个更简单的子问题，然后用这个简化后的问题去检索，以扩大召回范围、避免原始复杂问题与向量库内容匹配度过低。
            """,
            #   定义输入变量
            input_variables=["query"],
        )

# 主程序
if __name__ == "__main__":
    rag_prompt = RAGPrompts.rag_prompt()
    result = rag_prompt.format(
        context="校园赛事管理系统支持多种比赛类型，包括程序设计竞赛、数学建模竞赛、创新创业大赛、英语演讲比赛等。",
        question="校园赛事管理系统支持哪些比赛类型？",
        history="",
        phone="010-12345678",
    )
    print(result)
