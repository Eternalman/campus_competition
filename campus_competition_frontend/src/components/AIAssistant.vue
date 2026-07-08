 <template>
  <div class="ai-assistant-nav">
    <div class="nav-item ai-nav-item" @click="showDialog = true">
      赛事AI助手
    </div>

    <el-dialog
      v-model="showDialog"
      width="600px"
      :close-on-click-modal="false"
      class="ai-assistant-dialog"
    >
      <template #header>
        <div class="dialog-header">
          <span class="dialog-title">高校赛事AI助手</span>
          <el-button text type="primary" @click="handleNewChat" :loading="loading" size="small">
            <el-icon><Plus /></el-icon>
            新建对话
          </el-button>
        </div>
      </template>
      <div class="chat-container">
        <div class="messages-list" ref="messagesListRef">
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <div class="message-avatar">
              <el-icon v-if="msg.role === 'assistant'" size="24"><Service /></el-icon>
              <el-avatar v-else :size="24" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
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
              <el-icon size="24"><Service /></el-icon>
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
      </div>
      <template #footer>
        <div class="input-area">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="2"
            placeholder="请输入您的问题..."
            @keydown.ctrl.enter="handleSend"
            clearable
          />
          <el-button type="primary" @click="handleSend" :loading="loading" class="send-btn">
            发送
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Service, Plus } from '@element-plus/icons-vue'
import { useRagChat } from '@/composables/useRagChat'
import { ElMessage } from 'element-plus'

const showDialog = ref(false)
const inputMessage = ref('')
const messagesListRef = ref(null)
let initialized = false

// 使用 RAG composable 管理聊天逻辑
const { messages, loading, init, sendMessage: ragSend, newConversation } = useRagChat({
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

// 监听消息变化，自动滚动
watch(messages, () => {
  scrollToBottom()
}, { deep: true })

// 弹窗打开时初始化会话
watch(showDialog, async (val) => {
  if (val && !initialized) {
    await init()
    initialized = true
  }
})

const sendQuickQuestion = (question) => {
  inputMessage.value = question
  handleSend()
}

const handleNewChat = async () => {
  await newConversation()
  ElMessage.success('已创建新对话')
  scrollToBottom()
}

const handleSend = async () => {
  const question = inputMessage.value.trim()
  if (!question) {
    ElMessage.warning('请输入您的问题')
    return
  }

  inputMessage.value = ''
  await ragSend(question)
}
</script>

<style scoped>
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.dialog-title {
  font-size: 18px;
  font-weight: 600;
}

.ai-assistant-nav {
  display: flex;
  align-items: center;
}

.ai-nav-item {
  font-size: 16px;
  color: #606266;
  text-decoration: none;
  transition: all 0.2s;
  padding-bottom: 4px;
  border-bottom: 2px solid transparent;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.ai-nav-item:hover {
  color: #409eff;
  border-bottom-color: #409eff;
}

.chat-container {
  max-height: 400px;
  display: flex;
  flex-direction: column;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0;
  max-height: 320px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
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
  width: 36px;
  height: 36px;
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
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.message.assistant .message-text {
  background: #f0f7ff;
  color: #303133;
  border-top-left-radius: 4px;
}

.message-refs {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.ref-label {
  font-size: 11px;
  color: #909399;
}

.ref-tag {
  font-size: 10px;
}

.message.user .message-text {
  background: #409eff;
  color: white;
  border-top-right-radius: 4px;
}

.typing-indicator {
  padding: 12px 16px;
  background: #f0f7ff;
  border-radius: 12px;
  border-top-left-radius: 4px;
  display: flex;
  gap: 4px;
  align-items: center;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #909399;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}

.quick-questions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: flex-start;
}

.quick-label {
  color: #909399;
  font-size: 13px;
  flex-shrink: 0;
  padding-top: 2px;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
}

.quick-tag:hover {
  background: #409eff;
  color: white;
  border-color: #409eff;
}

.input-area {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-area :deep(.el-textarea) {
  flex: 1;
}

.send-btn {
  height: 74px;
  padding: 0 24px;
}
</style>
