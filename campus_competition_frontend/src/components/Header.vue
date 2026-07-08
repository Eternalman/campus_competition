<template>
  <header class="header">
    <div class="header-content">
      <!-- Logo 区域 -->
      <div class="logo" @click="$router.push('/')">
        <el-icon><Trophy /></el-icon>
        校园赛事管理系统
      </div>

      <!-- 中间导航栏 -->
      <nav class="nav">
        <router-link to="/" class="nav-item" active-class="active">首页</router-link>
        <router-link to="/hot" class="nav-item" active-class="active">热门推荐</router-link>
        <router-link to="/profile" class="nav-item" active-class="active">个人中心</router-link>
        <router-link to="/ai-assistant" class="nav-item" active-class="active">
          赛事AI助手
        </router-link>
        <router-link to="/admin/login" class="nav-item" active-class="active">后台管理</router-link>
      </nav>

      <!-- 右侧功能区：搜索 + 通知铃铛 + 头像下拉菜单 -->
      <div class="header-right">
        <el-input 
          v-model="searchForm.keyword" 
          placeholder="输入关键词搜索赛事" 
          clearable 
          style="width: 240px;"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button @click="handleSearch" :icon="Search" />
          </template>
        </el-input>
        
        <!-- 全局通知铃铛 -->
        <GlobalNotice />
        
        <!-- 【核心修改】头像hover下拉菜单 -->
        <el-dropdown trigger="hover" placement="bottom-end" hide-on-click>
          <!-- 头像区域：点击不跳转，仅hover触发下拉 -->
          <div class="avatar-wrapper">
            <el-avatar 
              :size="32" 
              src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" 
              class="user-avatar"
            />
          </div>
          <!-- 下拉菜单内容 -->
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="goToProfile">
                <el-icon><Setting /></el-icon>
                个人设置
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout" style="color: #f56c6c;">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup>
// 必须的依赖导入，确保功能正常
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElInput, ElButton, ElAvatar, ElMessage, ElDropdown, ElDropdownItem } from 'element-plus'
import { Trophy, Search, Setting, SwitchButton, ChatDotRound } from '@element-plus/icons-vue'
import GlobalNotice from '@/components/GlobalNotice.vue'



const router = useRouter()
// 搜索表单
const searchForm = ref({
  keyword: ''
})

// 搜索逻辑
const handleSearch = () => {
  if (!searchForm.value.keyword.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  router.push({
    path: '/',
    query: { keyword: searchForm.value.keyword }
  })
}

// 点击个人设置，跳转到个人中心
const goToProfile = () => {
  router.push('/profile')
}

// 退出登录完整逻辑
const handleLogout = () => {
  // 清除本地存储的登录凭证
  // localStorage.removeItem('token')
  // localStorage.removeItem('userInfo')
  localStorage.removeItem('front_token')
  localStorage.removeItem('front_refreshToken')
  localStorage.removeItem('front_userInfo')
  ElMessage.success('退出登录成功')
  // 跳转到前台登录页
  router.push('/login')
}
</script>

<style scoped>
/* 头部固定定位，永远在页面最顶部、最上层 */
.header {
  width: 100%;
  height: 60px;
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  position: fixed;
  top: 0;
  left: 0;
  z-index: 9999;
}

/* 头部内容容器：适配所有屏幕宽度 */
.header-content {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 20px;
}

/* Logo：禁止压缩，避免变形 */
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
  cursor: pointer;
  flex-shrink: 0;
}

/* 导航栏：禁止压缩 */
.nav {
  display: flex;
  gap: 36px;
  flex-shrink: 0;
}

.nav-item {
  font-size: 16px;
  color: #606266;
  text-decoration: none;
  transition: all 0.2s;
  padding-bottom: 4px;
  border-bottom: 2px solid transparent;
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-item:hover,
.nav-item.active {
  color: #409eff;
  border-bottom-color: #409eff;
}

/* 右侧区域：禁止压缩，自动靠右 */
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-left: auto;
  flex-shrink: 0;
}

/* 头像容器样式 */
.avatar-wrapper {
  cursor: pointer;
  line-height: 0;
}
.user-avatar {
  transition: transform 0.2s;
}
.avatar-wrapper:hover .user-avatar {
  transform: scale(1.1);
}
</style>