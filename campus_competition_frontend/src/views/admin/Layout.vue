<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ isCollapse: isCollapse }">
      <div class="logo">
        <h2 v-if="!isCollapse">赛事管理后台</h2>
        <el-icon v-else><Menu /></el-icon>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :unique-opened="true"
        router
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409eff"
      >
        <el-menu-item index="/admin/competition">
          <el-icon><Trophy /></el-icon>
          <template #title>赛事管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/category">
          <el-icon><List /></el-icon>
          <template #title>赛事分类</template>
        </el-menu-item>
        <el-menu-item index="/admin/user">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        <el-sub-menu index="registration">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>报名管理</span>
          </template>
          <el-menu-item index="/admin/registration">报名列表</el-menu-item>
          <el-menu-item index="/admin/score-management">评分管理</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="operation">
          <template #title>
            <el-icon><Operation /></el-icon>
            <span>运营管理</span>
          </template>
          <el-menu-item index="/admin/notice">通知公告</el-menu-item>
          <el-menu-item index="/admin/knowledge-base">知识库管理</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="log" v-if="userInfo.role === 'admin'">
          <template #title>
            <el-icon><DocumentCopy /></el-icon>
            <span>日志管理</span>
          </template>
          <el-menu-item index="/admin/login-log">登录日志</el-menu-item>
          <el-menu-item index="/admin/operation-log">操作日志</el-menu-item>
          <el-menu-item index="/admin/error-log">错误日志</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/admin/statistics">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>统计分析</template>
        </el-menu-item>
        <el-menu-item index="/admin/message">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>留言管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/system-info" v-if="userInfo.role === 'admin'">
          <el-icon><InfoFilled /></el-icon>
          <template #title>系统信息</template>
        </el-menu-item>
      </el-menu>
      <div class="collapse-btn" @click="isCollapse = !isCollapse">
        <el-icon><Expand v-if="isCollapse" /><Fold v-else /></el-icon>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main" :class="{ isCollapse: isCollapse }">
      <header class="header">
        <div class="header-left">
          <el-button type="text" @click="isCollapse = !isCollapse">
            <el-icon><Menu /></el-icon>
          </el-button>
        </div>
        <div class="header-right">
          <el-button type="text" @click="goFront">前台预览</el-button>
          <span>{{ userInfo.role === 'admin' ? '管理员' : '评委' }}[{{ userInfo.username }}]</span>
          <el-button type="text" @click="handleLogout">退出</el-button>
        </div>
      </header>
      <div class="content"><router-view /></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const isCollapse = ref(false)

// 获取当前路由用于菜单高亮
const activeMenu = computed(() => route.path)

// 从localStorage获取用户信息（使用 admin 前缀）
const userInfo = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('admin_userInfo') || '{}')
  } catch {
    return { username: 'admin' }
  }
})

// 跳转到前台
const goFront = () => {
  window.open('/', '_blank')
}

// 退出登录
const handleLogout = () => {
  ElMessageBox.confirm('确定要退出后台管理吗？', '提示', {
    type: 'warning'
  }).then(() => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_refreshToken')
    localStorage.removeItem('admin_userInfo')
    ElMessage.success('退出成功')
    router.push('/admin/login')
  }).catch(() => {})
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
  background-color: #f0f2f5;
}
.sidebar {
  width: 220px;
  min-height: 100vh;
  background-color: #001529;
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
}
.sidebar.isCollapse {
  width: 64px;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo h2 {
  font-size: 18px;
  margin: 0;
}
.logo .el-icon {
  font-size: 24px;
}
.sidebar .el-menu {
  flex: 1;
  border-right: none;
}
.collapse-btn {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  border-top: 1px solid rgba(255,255,255,0.1);
  font-size: 20px;
}
.collapse-btn:hover {
  background-color: rgba(255,255,255,0.1);
}
.main {
  flex: 1;
  margin-left: 220px;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s;
  min-height: 100vh;
}
.main.isCollapse {
  margin-left: 64px;
}
.header {
  height: 60px;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}
.header-right span {
  color: #606266;
}
.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
</style>