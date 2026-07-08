import { ref } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
const ACTIVE_SESSION_KEY = 'rag_active_session'

/**
 * RAG 聊天 Composable
 *
 * 支持多会话管理：会话列表、切换会话、新建对话。
 * 供独立页面版和导航栏弹窗版 AI 助手共用。
 *
 * @param {Object} options
 * @param {string} options.welcomeMessage - 初始欢迎消息（HTML 格式）
 * @returns {{ messages, loading, sessionId, conversations, init, sendMessage,
 *             newConversation, switchConversation, clearHistory, deleteAllConversations }}
 */
export function useRagChat(options = {}) {
  const {
    welcomeMessage = '您好！我是高校赛事AI助手，很高兴为您服务！😊<br><br>我可以帮您解答关于赛事系统的各种问题，试试点击下方的快捷提问吧！'
  } = options

  // ==================== 状态 ====================
  const messages = ref([])
  const loading = ref(false)
  const sessionId = ref('')
  const conversations = ref([])

  // ==================== 工具函数 ====================
  const apiUrl = (path) => `${API_BASE}/rag${path}`

  /**
   * 获取认证请求头，自动携带 front_token
   */
  const getAuthHeaders = () => {
    const headers = { 'Content-Type': 'application/json' }
    const token = localStorage.getItem('front_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    } else {
      console.warn('[RAG] 未找到登录 token，对话将作为匿名用户处理，无法与已登录用户的对话隔离')
    }
    return headers
  }

  // ==================== 会话管理 ====================

  /**
   * 调用后端创建新会话
   */
  const createSession = async () => {
    try {
      const res = await fetch(apiUrl('/session/'), { method: 'POST' })
      const data = await res.json()
      return data.session_id
    } catch (e) {
      console.error('创建会话失败:', e)
      return null
    }
  }

  /**
   * 加载会话列表（从后端）
   */
  const loadConversationList = async () => {
    try {
      const res = await fetch(apiUrl('/sessions/'))
      const data = await res.json()
      conversations.value = data.sessions || []
    } catch (e) {
      console.error('加载会话列表失败:', e)
    }
  }

  /**
   * 加载指定会话的历史消息
   */
  const loadHistory = async (sid) => {
    if (!sid) return
    try {
      const res = await fetch(apiUrl(`/session/${sid}/history/`))
      const data = await res.json()
      if (data.history && data.history.length > 0) {
        const historyMessages = []
        for (const h of data.history) {
          historyMessages.push({ role: 'user', content: h.question })
          historyMessages.push({ role: 'assistant', content: h.answer })
        }
        messages.value = [
          ...historyMessages,
          { role: 'assistant', content: welcomeMessage }
        ]
      } else {
        messages.value = [{ role: 'assistant', content: welcomeMessage }]
      }
    } catch (e) {
      console.error('加载历史失败:', e)
      messages.value = [{ role: 'assistant', content: welcomeMessage }]
    }
  }

  /**
   * 初始化：恢复上次活跃会话或创建新会话
   */
  const init = async () => {
    await loadConversationList()

    // 尝试恢复上次活跃会话
    const lastActive = localStorage.getItem(ACTIVE_SESSION_KEY)
    if (lastActive) {
      sessionId.value = lastActive
      await loadHistory(lastActive)
    } else {
      await newConversation()
    }
  }

  /**
   * 新建对话
   */
  const newConversation = async () => {
    const newId = await createSession()
    if (!newId) return

    sessionId.value = newId
    localStorage.setItem(ACTIVE_SESSION_KEY, newId)
    messages.value = [{ role: 'assistant', content: welcomeMessage }]
  }

  /**
   * 切换到指定会话
   */
  const switchConversation = async (sid) => {
    if (sid === sessionId.value) return
    sessionId.value = sid
    localStorage.setItem(ACTIVE_SESSION_KEY, sid)
    await loadHistory(sid)
  }

  // ==================== 消息发送 ====================

  /**
   * 发送问题，统一使用 /query/（普通 HTTP JSON）。
   * 发送完成后自动刷新会话列表。
   */
  const sendMessage = async (question) => {
    if (!sessionId.value) {
      const newId = await createSession()
      if (!newId) {
        messages.value.push({
          role: 'assistant',
          content: '抱歉，无法建立会话连接，请稍后再试。'
        })
        return
      }
      sessionId.value = newId
      localStorage.setItem(ACTIVE_SESSION_KEY, newId)
    }

    messages.value.push({ role: 'user', content: question })
    loading.value = true

    const assistantMsg = { role: 'assistant', content: '', references: [] }
    messages.value.push(assistantMsg)

    try {
      const queryRes = await fetch(apiUrl('/query/'), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          query: question,
          session_id: sessionId.value,
        }),
      })

      if (!queryRes.ok) {
        throw new Error(`HTTP ${queryRes.status}`)
      }

      const queryData = await queryRes.json()

      if (queryData.answer) {
        assistantMsg.content = queryData.answer
        assistantMsg.references = queryData.references || []
      } else {
        assistantMsg.content = '未找到对应的答案，请尝试换个问法。'
      }
      messages.value = [...messages.value]

      // 发送完成后刷新会话列表（侧边栏实时更新）
      await loadConversationList()
    } catch (e) {
      console.error('查询失败:', e)
      if (!assistantMsg.content) {
        assistantMsg.content = '抱歉，服务暂时不可用，请稍后再试。'
      }
      messages.value = [...messages.value]
    } finally {
      loading.value = false
    }
  }

  // ==================== 清除 ====================

  /**
   * 清除当前会话的历史
   */
  const clearHistory = async () => {
    if (!sessionId.value) return
    try {
      await fetch(apiUrl(`/session/${sessionId.value}/clear_history/`), {
        method: 'DELETE',
      })
      messages.value = [{ role: 'assistant', content: welcomeMessage }]
      await loadConversationList()
    } catch (e) {
      console.error('清除历史失败:', e)
    }
  }

  /**
   * 删除全部会话（逐个清除）
   */
  const deleteAllConversations = async () => {
    try {
      for (const conv of conversations.value) {
        await fetch(apiUrl(`/session/${conv.session_id}/clear_history/`), {
          method: 'DELETE',
        })
      }
      conversations.value = []
      await newConversation()
    } catch (e) {
      console.error('删除全部会话失败:', e)
    }
  }

  /**
   * 删除单个会话
   */
  const deleteConversation = async (sid) => {
    try {
      await fetch(apiUrl(`/session/${sid}/clear_history/`), {
        method: 'DELETE',
      })
      // 如果删除的是当前活跃会话，切换到新会话
      if (sid === sessionId.value) {
        await newConversation()
      }
      await loadConversationList()
    } catch (e) {
      console.error('删除会话失败:', e)
    }
  }

  return {
    messages,
    loading,
    sessionId,
    conversations,
    init,
    sendMessage,
    newConversation,
    switchConversation,
    clearHistory,
    deleteAllConversations,
    deleteConversation,
    loadConversationList,
  }
}
