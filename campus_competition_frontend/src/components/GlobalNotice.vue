<template>
  <div class="global-notice">
    <!-- 通知铃铛按钮 -->
    <div class="notice-bell-wrapper" @click="handleBellClick">
      <el-icon class="bell-icon"><Bell /></el-icon>
      <!-- 红色数字徽章：只有未读数量>0时显示 -->
      <el-badge 
        :value="unreadCount" 
        :hidden="unreadCount === 0" 
        class="notice-badge" 
        type="danger"
      />
    </div>

    <!-- 右侧通知抽屉：去掉append-to-body，避免样式异常 -->
    <el-drawer
      v-model="drawerVisible"
      size="360px"
      direction="rtl"
      :with-header="false"
      class="notice-drawer"
    >
      <!-- 自定义抽屉头部：标题 + 清除按钮 -->
      <div class="drawer-header">
        <span class="drawer-title">系统通知</span>
        <el-button 
          type="danger" 
          link 
          size="small" 
          @click="handleClearNotices"
          :disabled="noticeList.length === 0"
        >
          <el-icon><Delete /></el-icon>
          清除通知
        </el-button>
      </div>

      <!-- 通知列表 -->
      <div class="notice-list" v-loading="loading">
        <div
          v-for="notice in noticeList"
          :key="notice.id"
          class="notice-item"
        >
          <div class="notice-title">{{ notice.title || '无标题' }}</div>
          <div class="notice-time">{{ formatTime(notice.create_time) }}</div>
          <div class="notice-content">{{ notice.content || '无内容' }}</div>
        </div>
        <el-empty v-if="noticeList.length === 0 && !loading" description="暂无通知" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Bell, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const drawerVisible = ref(false)
const noticeList = ref([])
const loading = ref(false)
// 未读数量状态，独立控制红色徽章
const unreadCount = ref(0)
// 定时器引用
let refreshTimer = null
// localStorage key
const LAST_VIEW_TIME_KEY = 'notice_last_view_time'

// 获取最后查看时间
const getLastViewTime = () => {
  const time = localStorage.getItem(LAST_VIEW_TIME_KEY)
  return time ? new Date(time) : new Date(0)
}

// 更新最后查看时间为当前时间
const updateLastViewTime = () => {
  const now = new Date().toISOString()
  localStorage.setItem(LAST_VIEW_TIME_KEY, now)
}

// 计算未读通知数量
const calculateUnreadCount = (notices) => {
  const lastViewTime = getLastViewTime()
  return notices.filter(notice => {
    const noticeTime = new Date(notice.create_time)
    return noticeTime > lastViewTime
  }).length
}

// 点击铃铛：打开抽屉 + 更新最后查看时间 + 消除红色数字
const handleBellClick = () => {
  drawerVisible.value = true
  // 更新最后查看时间为当前时间
  updateLastViewTime()
  // 打开抽屉的同时，把未读数量清零
  unreadCount.value = 0
}

// 清除通知功能：先关闭抽屉再显示确认框，避免被遮挡
const handleClearNotices = async () => {
  // 先关闭抽屉
  drawerVisible.value = false
  
  // 等待抽屉关闭后再显示确认框
  setTimeout(async () => {
    try {
      await ElMessageBox.confirm(
        '确定要清除所有通知吗？',
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      // 确认后清空通知列表
      noticeList.value = []
      ElMessage.success('通知已清除')
    } catch (error) {
      // 用户点击取消，不做任何操作
    }
  }, 300)
}

// 获取最新公告列表
const fetchNoticeList = async () => {
  loading.value = true
  try {
    const res = await request.get('/notices/latest/')
    noticeList.value = Array.isArray(res) ? res : []
    // 计算未读通知数量（只统计最后查看时间之后的新通知）
    unreadCount.value = calculateUnreadCount(noticeList.value)
  } catch (err) {
    console.error('获取通知列表失败：', err)
    ElMessage.error('获取通知失败，请稍后重试')
    noticeList.value = []
  } finally {
    loading.value = false
  }
}

// 格式化时间 - 使用北京时间
const formatTime = (timeStr) => {
  if (!timeStr) return '未知时间'
  try {
    const date = new Date(timeStr)
    if (isNaN(date.getTime())) {
      return '时间格式错误'
    }
    // 强制使用北京时间格式化
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (e) {
    return '未知时间'
  }
}

onMounted(() => {
  fetchNoticeList()
  // 定时刷新通知（每5分钟）
  refreshTimer = setInterval(fetchNoticeList, 5 * 60 * 1000)
})

onUnmounted(() => {
  // 清理定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.global-notice {
  position: relative;
  display: inline-block;
  cursor: pointer;
}

.notice-bell-wrapper {
  position: relative;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #409eff;
  transition: all 0.3s ease;
}

.notice-bell-wrapper:hover {
  color: #66b1ff;
  transform: scale(1.1);
}

.notice-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  z-index: 99;
}

/* 抽屉样式优化 */
.notice-drawer :deep(.el-drawer__body) {
  padding: 0;
}

/* 自定义抽屉头部 */
.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  background-color: #fff;
}

.drawer-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

/* 通知列表 */
.notice-list {
  padding: 0 20px;
  max-height: calc(100vh - 60px);
  overflow-y: auto;
}

.notice-item {
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.notice-item:last-child {
  border-bottom: none;
}

.notice-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.notice-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.notice-content {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}
</style>