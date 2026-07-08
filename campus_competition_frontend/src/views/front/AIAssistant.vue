<template>
  <div class="ai-page">
    <!-- ===== 侧边栏 ===== -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <el-button type="primary" @click="handleNewConversation" class="new-btn" :loading="loading">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
        <el-button @click="handleDeleteAll" class="clear-all-btn" :disabled="conversations.length === 0">
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>

      <div class="history-title">历史对话</div>

      <div class="history-list">
        <div
          v-for="conv in conversations"
          :key="conv.session_id"
          :class="['history-item', { active: conv.session_id === sessionId }]"
          @click="handleSwitchConversation(conv.session_id)"
        >
          <div class="history-item-main">
            <div class="history-item-title">{{ conv.title }}</div>
            <div class="history-item-time">{{ formatTime(conv.updated_at) }}</div>
          </div>
          <el-button
            text
            size="small"
            class="history-delete-btn"
            @click.stop="handleDeleteConversation(conv.session_id)"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <el-empty v-if="conversations.length === 0" description="暂无历史对话" :image-size="60" />
      </div>
    </aside>

    <!-- ===== 聊天区 ===== -->
    <main class="chat-main">
      <div class="chat-wrapper">
        <div class="chat-container">
          <div class="messages-list" ref="messagesListRef">
            <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
              <div class="message-avatar">
                <el-icon v-if="msg.role === 'assistant'" size="28"><Service /></el-icon>
                <el-avatar v-else :size="28" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
              </div>
              <div class="message-content">
                <div class="message-text" v-html="msg.content"></div>
                <div v-if="msg.references && msg.references.length > 0" class="message-refs">
                  <span class="ref-label">📚 参考来源：</span>
                  <el-tag v-for="ref in msg.references" :key="ref" size="small" type="info" class="ref-tag">{{ ref }}</el-tag>
                </div>
              </div>
            </div>
            <div v-if="loading" class="message assistant">
              <div class="message-avatar">
                <el-icon size="28"><Service /></el-icon>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <div class="quick-questions">
            <span class="quick-label">快捷提问：</span>
            <el-tag v-for="q in quickQuestions" :key="q" class="quick-tag" @click="sendQuickQuestion(q)">
              {{ q }}
            </el-tag>
          </div>

          <div class="input-area">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="2"
              placeholder="请输入您的问题..."
              @keydown.ctrl.enter="handleSend"
              clearable
            />
            <el-button type="primary" @click="handleSend" :loading="loading" class="send-btn" size="large">
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Service, Promotion, Plus, Delete, Close } from '@element-plus/icons-vue'
import { useRagChat } from '@/composables/useRagChat'
import dayjs from 'dayjs'

const inputMessage = ref('')
const messagesListRef = ref(null)

const { messages, loading, sessionId, conversations, init, sendMessage: ragSend,
        newConversation, switchConversation, deleteAllConversations, deleteConversation } = useRagChat({
  welcomeMessage: '您好！我是高校赛事AI助手，很高兴为您服务！😊<br><br>我可以帮您解答关于赛事系统的各种问题，试试点击下方的快捷提问吧！'
})

const quickQuestions = [
  '当前有多少个赛事活动',
  '有哪些热门赛事',
  '如何修改密码',
  '如何报名参加赛事',
  '如何取消报名',
  '我的报名记录在哪里查看',
  '如何查看成绩',
  '如何修改个人信息',
  '如何注册账号',
  '如何发布新赛事'
]

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesListRef.value) {
      messagesListRef.value.scrollTop = messagesListRef.value.scrollHeight
    }
  })
}

watch(messages, () => scrollToBottom(), { deep: true })

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  return dayjs(isoStr).format('MM-DD HH:mm')
}

// ===== 事件处理 =====

const handleNewConversation = async () => {
  await newConversation()
  ElMessage.success('已创建新对话')
}

const handleDeleteAll = async () => {
  try {
    await ElMessageBox.confirm('确定要清空全部历史对话吗？此操作不可恢复。', '确认清空', {
      type: 'warning',
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
    })
    await deleteAllConversations()
    ElMessage.success('已清空全部历史对话')
  } catch (_) {
    // 用户取消
  }
}

const handleDeleteConversation = async (sid) => {
  try {
    await ElMessageBox.confirm('确定要删除该对话吗？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteConversation(sid)
    ElMessage.success('已删除')
  } catch (_) {
    // 用户取消
  }
}

const handleSwitchConversation = async (sid) => {
  await switchConversation(sid)
  scrollToBottom()
}

const sendQuickQuestion = (question) => {
  inputMessage.value = question
  handleSend()
}

const handleSend = async () => {
  const question = inputMessage.value.trim()
  if (!question) {
    ElMessage.warning('请输入您的问题')
    return
  }
  inputMessage.value = ''
  await ragSend(question)
  scrollToBottom()
}

onMounted(() => {
  init()
})
</script>

<style scoped>
/* ===== 整体布局 ===== */
.ai-page {
  display: flex;
  height: calc(100vh - 60px);
  background: #f5f7fa;
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 280px;
  min-width: 280px;
  background: #fff;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.sidebar-header {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.new-btn {
  flex: 1;
}

.clear-all-btn {
  width: 40px;
  padding: 0;
}

.history-title {
  font-size: 14px;
  font-weight: 600;
  color: #909399;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.history-list {
  flex: 1;
  overflow-y: auto;
}

.history-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  transition: all 0.2s;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  gap: 4px;
}

.history-item:hover {
  background: #f0f7ff;
}

.history-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}

.history-item-main {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  font-size: 14px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.history-item-time {
  font-size: 12px;
  color: #c0c4cc;
}

.history-delete-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;
  color: #f56c6c;
}

.history-item:hover .history-delete-btn {
  opacity: 1;
}

/* ===== 聊天区 ===== */
.chat-main {
  flex: 1;
  display: flex;
  justify-content: center;
  overflow: hidden;
}

.chat-wrapper {
  width: 100%;
  max-width: 900px;
  background: #fff;
  margin: 0;
  display: flex;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.message {
  display: flex;
  gap: 14px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message.user .message-avatar {
  background: #f0f2f5;
}

.message-content {
  max-width: 70%;
}

.message-text {
  padding: 14px 18px;
  border-radius: 14px;
  line-height: 1.7;
  word-break: break-word;
  font-size: 15px;
}

.message.assistant .message-text {
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f4ff 100%);
  color: #303133;
  border-top-left-radius: 4px;
}

.message-refs {
  margin-top: 8px;
  padding: 0 4px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.ref-label {
  font-size: 12px;
  color: #909399;
}

.ref-tag {
  font-size: 11px;
}

.message.user .message-text {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
  border-top-right-radius: 4px;
}

.typing-indicator {
  padding: 14px 18px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f4ff 100%);
  border-radius: 14px;
  border-top-left-radius: 4px;
  display: flex;
  gap: 5px;
  align-items: center;
}

.typing-indicator span {
  width: 10px;
  height: 10px;
  background: #909399;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-10px); opacity: 1; }
}

.quick-questions {
  padding: 16px 24px;
  border-top: 1px solid #ebeef5;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
  background: #fafafa;
}

.quick-label {
  color: #909399;
  font-size: 14px;
  flex-shrink: 0;
  padding-top: 2px;
  font-weight: 500;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}

.quick-tag:hover {
  background: #409eff;
  color: white;
  border-color: #409eff;
  transform: translateY(-1px);
}

.input-area {
  padding: 20px 24px 24px;
  display: flex;
  gap: 16px;
  align-items: flex-end;
  border-top: 1px solid #ebeef5;
  background: #fff;
}

.input-area :deep(.el-textarea) { flex: 1; }

.send-btn {
  height: 74px;
  padding: 0 28px;
  font-size: 16px;
  font-weight: 500;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.send-btn:hover {
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}
</style>
