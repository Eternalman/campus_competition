<template>
  <div class="profile-page">
    <!-- 顶部用户信息卡片 + 头像上传 -->
    <div class="profile-header">
      <!-- 头像上传 -->
      <el-upload
        class="avatar-uploader"
        action="/api/upload/"
        :show-file-list="false"
        :on-success="handleAvatarSuccess"
        :headers="uploadHeaders"
      >
        <el-avatar :size="80" :src="userInfo.avatar || defaultAvatar" />
        <div class="avatar-tip">点击更换头像</div>
      </el-upload>

      <div class="user-info">
        <h2 class="username">{{ userInfo.nickname || userInfo.username }}</h2>
        <p class="intro">{{ userInfo.intro || '这个人很懒，什么都没写' }}</p>
      </div>
    </div>

    <!-- 标签页 -->
    <div class="profile-content">
      <el-tabs v-model="activeTab">
        <!-- 1. 我的报名列表 -->
        <el-tab-pane label="我的报名" name="registrations">
          <div class="registration-table">
            <!-- 加载状态 -->
            <el-skeleton v-if="regLoading" animated />
            <!-- 空数据 -->
            <el-empty v-else-if="registrationList.length === 0" description="暂无报名记录" />
            <!-- 报名列表 -->
            <el-table v-else :data="registrationList" border stripe>
              <el-table-column label="赛事名称" prop="competition_title" />
              <el-table-column label="报名姓名" prop="name" />
              <el-table-column label="联系电话" prop="phone" />
              <el-table-column label="报名时间" width="180">
                <template #default="{ row }">
                  {{ formatTime(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="成绩" width="120">
                <template #default="{ row }">
                  <span v-if="row.score" style="color: #67c23a; font-weight: 600;">{{ row.score }}</span>
                  <span v-else style="color: #909399;">-</span>
                </template>
              </el-table-column>
              <el-table-column label="报名状态" width="120">
                <template #default="scope">
                  <el-tag :type="scope.row.status === 'normal' ? 'success' : (scope.row.status === 'finished' ? 'warning' : 'info')">
                    {{ scope.row.status_display }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 2. 个人信息 -->
        <el-tab-pane label="个人信息" name="info">
          <el-form
            ref="formRef"
            :model="userInfo"
            label-width="100px"
            class="info-form"
          >
            <el-form-item label="账号">
              <el-input v-model="userInfo.username" disabled />
            </el-form-item>
            <el-form-item label="昵称">
              <el-input v-model="userInfo.nickname" placeholder="请输入昵称" maxlength="20" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="userInfo.phone" placeholder="请输入手机号" maxlength="11" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="userInfo.email" placeholder="请输入邮箱" />
            </el-form-item>
            <el-form-item label="个人简介">
              <el-input
                v-model="userInfo.intro"
                type="textarea"
                :rows="3"
                placeholder="介绍一下自己吧"
                maxlength="200"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saveLoading" @click.prevent="handleSave" native-type="button">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 3. 密码修改 -->
        <el-tab-pane label="密码修改" name="password">
          <el-form
            ref="pwdFormRef"
            :model="pwdForm"
            :rules="pwdRules"
            label-width="100px"
            class="pwd-form"
          >
            <el-form-item label="原密码" prop="oldPassword">
              <el-input v-model="pwdForm.oldPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input v-model="pwdForm.newPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="pwdForm.confirmPassword" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="pwdLoading" @click="handleChangePwd">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 4. 留言反馈 -->
        <el-tab-pane label="留言反馈" name="message">
          <el-form
            ref="messageFormRef"
            :model="messageForm"
            :rules="messageRules"
            label-width="100px"
            class="message-form"
          >
            <el-form-item label="标题" prop="title">
              <el-input v-model="messageForm.title" placeholder="请输入留言标题" maxlength="100" />
            </el-form-item>
            <el-form-item label="内容" prop="content">
              <el-input
                v-model="messageForm.content"
                type="textarea"
                :rows="5"
                placeholder="请输入留言内容"
              />
            </el-form-item>
            <el-form-item label="姓名" prop="name">
              <el-input v-model="messageForm.name" placeholder="请输入姓名" maxlength="20" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="messageForm.email" placeholder="请输入邮箱（选填）" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="messageForm.phone" placeholder="请输入手机号（选填）" maxlength="11" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="messageLoading" @click="handleSubmitMessage">
                提交留言
              </el-button>
              <el-button @click="handleResetMessage">
                重置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'
import { formatTime } from '@/utils/format'

// 默认头像
const defaultAvatar = 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'
const activeTab = ref('registrations')
const saveLoading = ref(false)
const pwdLoading = ref(false)
const regLoading = ref(false)
const messageLoading = ref(false)

// 用户信息
const userInfo = ref({
  username: '',
  nickname: '',
  phone: '',
  email: '',
  intro: '',
  avatar: ''
})

// 密码表单
const pwdFormRef = ref()
const pwdForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const pwdRules = ref({
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.value.newPassword) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
})

// 留言表单
const messageFormRef = ref()
const messageForm = ref({
  title: '',
  content: '',
  name: '',
  email: '',
  phone: ''
})
const messageRules = ref({
  title: [{ required: true, message: '请输入留言标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入留言内容', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
})

// 我的报名列表
const registrationList = ref([])

// 上传请求头
const uploadHeaders = ref({
  Authorization: 'Bearer ' + localStorage.getItem('front_token')
})

// 获取用户信息
const getUserInfo = async () => {
  try {
    const res = await request.get('/users/me/')
    userInfo.value = res
  } catch (err) {
    ElMessage.error('获取用户信息失败')
  }
}

// 保存个人信息
const handleSave = async () => {
  if (saveLoading.value) return // 防止重复点击
  
  saveLoading.value = true
  try {
    // 发起请求
    const result = await request.put('/users/update_profile/', userInfo.value)
    console.log('请求结果:', result)
    
    // 手动更新本地数据，不需要重新请求
    if (result) {
      Object.assign(userInfo.value, result)
      // 更新 localStorage 中的 userInfo
      const localUserInfo = localStorage.getItem('front_userInfo')
      if (localUserInfo) {
        const parsed = JSON.parse(localUserInfo)
        Object.assign(parsed, result)
        localStorage.setItem('front_userInfo', JSON.stringify(parsed))
      }
    }
    
    // 直接显示提示
    ElMessage.success('个人信息修改成功')
  } catch (err) {
    console.error('修改失败:', err)
    ElMessage.error('修改失败')
  } finally {
    saveLoading.value = false
  }
}

// 头像上传
const handleAvatarSuccess = (res) => {
  userInfo.value.avatar = res.file_url
  ElMessage.success({ message: '头像上传成功', zIndex: 99999 })
}

// 修改密码
const handleChangePwd = async () => {
  await pwdFormRef.value.validate()
  pwdLoading.value = true
  try {
    await request.put('/users/update_profile/', {
      password: pwdForm.value.newPassword,
      old_password: pwdForm.value.oldPassword
    })
    ElMessage.success('密码修改成功！请重新登录')
    pwdForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    setTimeout(() => {
      localStorage.clear()
      window.location.href = '/login'
    }, 1000)
  } catch (err) {
    ElMessage.error('原密码错误或修改失败')
  } finally {
    pwdLoading.value = false
  }
}

// 提交留言
const handleSubmitMessage = async () => {
  try {
    await messageFormRef.value.validate()
    messageLoading.value = true
    
    // 构建提交数据，邮箱和手机号为空时不传
    const submitData = { ...messageForm.value }
    if (!submitData.email) {
      delete submitData.email
    }
    if (!submitData.phone) {
      delete submitData.phone
    }
    
    console.log('提交留言数据:', submitData)
    await request.post('/messages/', submitData)
    
    ElMessage.success('留言提交成功，感谢您的反馈！')
    handleResetMessage()
  } catch (err) {
    console.error('提交留言失败:', err)
    if (err.response?.data) {
      console.error('错误详情:', err.response.data)
    }
    ElMessage.error('留言提交失败，请稍后重试')
  } finally {
    messageLoading.value = false
  }
}

// 重置留言表单
const handleResetMessage = () => {
  messageForm.value = {
    title: '',
    content: '',
    name: '',
    email: '',
    phone: ''
  }
  messageFormRef.value?.clearValidate()
}

// 获取我的报名
const getMyRegistrations = async () => {
  regLoading.value = true
  try {
    const res = await request.get('/registrations/my/')
    registrationList.value = res
  } catch (err) {
    ElMessage.error('获取报名记录失败')
  } finally {
    regLoading.value = false
  }
}

onMounted(() => {
  getUserInfo()
  getMyRegistrations()
})
</script>
<style scoped>
.profile-page { min-height: 100vh; background-color: #f5f7fa; }
.profile-header {
  max-width: 1000px; margin: 30px auto 0; padding: 30px;
  background: #fff; border-radius: 12px;
  display: flex; align-items: center; gap: 24px;
}
.avatar-uploader { cursor: pointer; position: relative; }
.avatar-tip {
  position: absolute; bottom: -20px; left: 50%;
  transform: translateX(-50%); font-size: 12px;
  color: #999; white-space: nowrap;
}
.user-info h2 { font-size: 24px; font-weight: 600; color: #303133; margin: 0 0 8px; }
.user-info p { font-size: 14px; color: #909399; margin: 0; }

.profile-content {
  max-width: 1000px; margin: 20px auto; padding: 0 0 30px;
  background: #fff; border-radius: 12px;
}
.info-form, .pwd-form, .message-form { max-width: 500px; padding: 30px; }
.registration-table { padding: 30px; }
</style>