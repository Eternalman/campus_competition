<template>
  <div class="front-register-page">
    <!-- 背景装饰（和登录页保持一致） -->
    <div class="bg-decoration">
      <div class="bg-world-map"></div>
      <div class="float-box box-1"></div>
      <div class="float-box box-2"></div>
      <div class="light-point point-1"></div>
      <div class="light-point point-2"></div>
      <div class="light-point point-3"></div>
      <div class="light-point point-4"></div>
      <div class="light-point point-5"></div>
    </div>

    <!-- 注册框 -->
    <div class="register-card">
      <div class="register-header">
        <div class="logo">
          <el-icon><Medal /></el-icon>
        </div>
        <h2>用户注册</h2>
      </div>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="register-form"
        @keyup.enter="handleRegister"
      >
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次确认密码"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item prop="nickname">
          <el-input
            v-model="registerForm.nickname"
            placeholder="请输入昵称（选填）"
            size="large"
            prefix-icon="UserFilled"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="register-btn"
            @click="handleRegister"
          >
            立即注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-link">
        已有账号？<router-link to="/login">去登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Medal, User, Lock, UserFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()
const registerFormRef = ref(null)
const loading = ref(false)

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  nickname: ''
})

// 自定义校验：两次密码一致
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3-20个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在6-20个字符之间', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        // 调用后端注册接口
        const registerData = {
          username: registerForm.username,
          password: registerForm.password,
          nickname: registerForm.nickname
        }
        await request.post('/auth/register/', registerData)
        
        ElMessage.success('注册成功！请登录')
        // 注册成功跳转到登录页
        router.push('/login')
      } catch (error) {
        console.error('注册失败:', error)
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.front-register-page {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #165DFF 0%, #0E2B5C 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 背景世界地图 */
.bg-world-map {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: url('https://picsum.photos/id/1015/1920/1080') center/cover no-repeat;
  opacity: 0.15;
  filter: brightness(0.8) contrast(1.2);
  z-index: 0;
}

/* 浮动方块装饰 */
.float-box {
  position: absolute;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  transform: rotate(45deg);
  z-index: 1;
  animation: float 15s infinite linear;
}
.box-1 {
  width: 180px;
  height: 180px;
  bottom: 10%;
  left: 10%;
  animation-duration: 20s;
}
.box-2 {
  width: 120px;
  height: 120px;
  top: 15%;
  right: 12%;
  animation-duration: 12s;
  animation-direction: reverse;
}

/* 光点装饰 */
.light-point {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.8);
  z-index: 1;
  animation: pulse 3s infinite ease-in-out;
}
.point-1 { top: 18%; left: 8%; animation-delay: 0s; }
.point-2 { top: 12%; left: 22%; animation-delay: 0.5s; }
.point-3 { top: 25%; right: 18%; animation-delay: 1s; }
.point-4 { bottom: 20%; right: 10%; animation-delay: 1.5s; }
.point-5 { bottom: 15%; left: 25%; animation-delay: 2s; }

/* 动画 */
@keyframes float {
  0% { transform: rotate(45deg) translate(0, 0); }
  50% { transform: rotate(45deg) translate(30px, 30px); }
  100% { transform: rotate(45deg) translate(0, 0); }
}
@keyframes pulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* 注册卡片 */
.register-card {
  width: 420px;
  padding: 40px 30px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  position: relative;
  z-index: 10;
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}
.logo {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #165DFF;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin: 0 auto 15px;
}
.register-header h2 {
  font-size: 18px;
  color: #303133;
  margin: 0;
  font-weight: 500;
}

.register-form {
  margin-top: 20px;
}
.register-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  background: #165DFF;
  border: none;
}

.login-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #909399;
}
.login-link a {
  color: #165DFF;
}
</style>