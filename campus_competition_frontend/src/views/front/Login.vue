<template>
  <div class="front-login-container">
    <div class="login-box">
      <div class="logo-box">
        <el-icon size="40" color="#409eff"><Trophy /></el-icon>
        <h2 class="title">用户登录</h2>
      </div>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        size="large"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            class="login-btn"
            @click="handleLogin"
            :loading="loading"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <router-link to="/register" class="register-link">注册新帐号</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Trophy } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()
const route = useRoute()
const loginFormRef = ref(null)
const loading = ref(false)

// 登录表单（响应式变量，拼写正确）
const loginForm = ref({
  username: '',
  password: ''
})

// 表单校验规则
const loginRules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    // 1. 先调用登录接口，获取JWT Token
    const loginRes = await request.post('/auth/login/', loginForm.value)
    
    // 2. 校验Token是否获取成功
    if (loginRes.access && loginRes.refresh) {
      // // 3. 保存Token到本地存储
      // localStorage.setItem('token', loginRes.access)
      // localStorage.setItem('refreshToken', loginRes.refresh)
      // 3. 保存Token到本地存储（使用 front 前缀）
      localStorage.setItem('front_token', loginRes.access)
      localStorage.setItem('front_refreshToken', loginRes.refresh)
      
      // 4. 调用新增的 /api/users/me/ 接口，获取完整用户信息
      const userRes = await request.get('/users/me/')
      // localStorage.setItem('userInfo', JSON.stringify(userRes))
      localStorage.setItem('front_userInfo', JSON.stringify(userRes))
      
      ElMessage.success('登录成功')
      
      // 5. 处理跳转逻辑
      const redirect = route.query.redirect
      if (redirect) {
        router.push(decodeURIComponent(redirect))
      } else {
        router.push('/')
      }
    } else {
      throw new Error('登录接口返回数据异常')
    }
  } catch (err) {
    console.error('登录失败', err)
    ElMessage.error(err.message || '登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}

// 页面加载时，已登录用户直接跳首页
onMounted(() => {
  // if (localStorage.getItem('token')) {
  if (localStorage.getItem('front_token')) {
    ElMessage.info('您已登录')
    router.push('/')
  }
})
</script>

<style scoped>
.front-login-container {
  width: 100vw;
  height: 100vh;
  /* background: url('https://picsum.photos/id/15/1920/1080') no-repeat center; */
  background: url('/bg.png') no-repeat center;
  background-size: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-box {
  width: 400px;
  padding: 40px 30px;
  /* background: rgba(255, 255, 255, 0.95); */
  background: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  /* box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  backdrop-filter: blur(4px); */
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.logo-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 30px;
}
.title {
  margin-top: 12px;
  color: #333;
  font-weight: 600;
}
.login-form {
  width: 100%;
}
.login-btn {
  width: 100%;
}
.register-link {
  display: block;
  text-align: center;
  margin-top: 16px;
  color: #409eff;
  font-size: 14px;
}
</style>