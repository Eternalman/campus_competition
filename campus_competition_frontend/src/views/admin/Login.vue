<template>
  <div class="admin-login-container">
    <div class="login-box">
      <h2 class="title">后台管理系统</h2>
      <el-form :model="loginForm" size="large" class="login-form">
        <el-form-item>
          <el-input
            v-model="loginForm.username"
            placeholder="请输入管理员或评委账号"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" @click="handleLogin" :loading="loading">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()
const loading = ref(false)

// 登录表单
const loginForm = ref({
  username: '',
  password: ''
})

// 登录核心逻辑
const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }

  loading.value = true
  try {
    const res = await request.post('/auth/admin-login/', loginForm.value)
    
    // 核心修复：只有接口返回了完整数据，才写入本地存储（使用 admin 前缀）
    if (res.access && res.user) {
      localStorage.setItem('admin_token', res.access)
      localStorage.setItem('admin_refreshToken', res.refresh)
      localStorage.setItem('admin_userInfo', JSON.stringify(res.user))
      
      ElMessage.success('登录成功')
      router.push('/admin/competition')
    } else {
      throw new Error('登录接口返回数据异常')
    }
  } catch (err) {
    console.error('后台登录失败', err)
  } finally {
    loading.value = false
  }
}

// 页面加载时，如果已经是管理员或评委登录，直接跳后台首页
onMounted(() => {
  const token = localStorage.getItem('admin_token')
  const userInfo = JSON.parse(localStorage.getItem('admin_userInfo') || '{}')
  if (token && (userInfo.role === 'admin' || userInfo.role === 'judge')) {
    router.push('/admin/competition')
  }
})
</script>

<style scoped>
.admin-login-container {
  width: 100vw;
  height: 100vh;
  /* background: linear-gradient(135deg, #1e3c72, #2a5298); */
  background: url('/bg.png') no-repeat center;
  background-size: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-box {
  width: 420px;
  padding: 40px;
  /* background: #fff; */
  background: rgba(255, 255, 255, 0.45);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
  font-weight: 600;
}
.login-form {
  width: 100%;
}
.login-btn {
  width: 100%;
}
</style>