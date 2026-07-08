<template>
  <div class="register-page">
    <!-- 报名表单 -->
    <div class="register-content" v-loading="loading">
      <div class="register-card">
        <h2 class="page-title">报名页面</h2>
        <!-- 赛事信息卡片 -->
        <div class="competition-info" v-if="competitionInfo">
          <p><span>赛事名称：</span>{{ competitionInfo.title }}</p>
          <p><span>竞赛时间：</span>{{ $formatTime(competitionInfo.competition_time) }}</p>
          <p><span>竞赛地点：</span>{{ competitionInfo.location }}</p>
          <p><span>报名时间：</span>{{ $formatTime(competitionInfo.registration_time) }}</p>
        </div>

        <!-- 报名表单 -->
        <el-form
          ref="formRef"
          :model="form"
          :rules="formRules"
          label-width="100px"
          class="register-form"
        >
          <el-form-item label="姓名" prop="name">
            <el-input v-model="form.name" placeholder="请输入姓名" />
          </el-form-item>
          <el-form-item label="身份证号" prop="id_card">
            <el-input v-model="form.id_card" placeholder="请输入身份证号" maxlength="18" />
          </el-form-item>
          <el-form-item label="联系电话" prop="phone">
            <el-input v-model="form.phone" placeholder="请输入手机号" maxlength="11" />
          </el-form-item>
          <el-form-item label="学校" prop="school">
            <el-input v-model="form.school" placeholder="请输入您的学校" />
          </el-form-item>
          <el-form-item label="备注" prop="remark">
            <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="输入备注信息，100字以内" maxlength="100" />
          </el-form-item>

          <!-- 附件上传（非必填） -->
          <el-form-item label="附件上传">
            <el-upload
              :action="uploadUrl"
              :headers="uploadHeaders"
              :accept="'.jpg,.jpeg,.png,.mp4,.avi,.mov'"
              :limit="1"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              :on-remove="handleFileRemove"
              :file-list="fileList"
              drag
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                拖放文件到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持格式：jpg/jpeg/png（图片）、mp4/avi/mov（视频），非必填
                </div>
              </template>
            </el-upload>
          </el-form-item>
        </el-form>

        <!-- 操作按钮 -->
        <div class="action-row">
          <el-button size="large" @click="$router.back()">返回</el-button>
          <el-button type="primary" size="large" :loading="submitLoading" @click="handleSubmit">提交</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Trophy, UploadFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()
const competitionId = route.params.id

// 基础数据
const loading = ref(false)
const submitLoading = ref(false)
const competitionInfo = ref({})
const formRef = ref()

// 表单数据
const form = ref({
  competition: competitionId,
  name: '',
  id_card: '',
  phone: '',
  school: '',
  remark: '',
  file_url: ''
})

// 上传相关
const fileList = ref([])
const uploadUrl = 'http://localhost:8000/api/upload/'
const uploadHeaders = ref({
  // 'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
    'Authorization': `Bearer ${localStorage.getItem('front_token') || ''}`
})

// 表单校验规则
const formRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  id_card: [
    { required: true, message: '请输入身份证号', trigger: 'blur' },
    { pattern: /^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/, message: '请输入正确的身份证号', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  school: [{ required: true, message: '请输入学校', trigger: 'blur' }]
}

// 上传回调
const handleUploadSuccess = (response) => {
  form.value.file_url = response.file_url
  ElMessage.success('文件上传成功！')
}

const handleUploadError = () => {
  ElMessage.error('文件上传失败，请重试！')
}

const handleFileRemove = () => {
  form.value.file_url = ''
}

// 获取赛事信息
const getCompetitionInfo = async () => {
  loading.value = true
  try {
    const res = await request.get(`/competitions/${competitionId}/`)
    competitionInfo.value = res
    form.value.competition = res.id
  } catch (err) {
    ElMessage.error('获取赛事信息失败')
    console.error(err)
  } finally {
    loading.value = false
  }
}

// 提交报名
const handleSubmit = async () => {
  await formRef.value?.validate()
  submitLoading.value = true
  try {
    await request.post('/registrations/', form.value)
    ElMessage.success('报名提交成功')
    router.push('/register/success')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '报名提交失败，请检查信息')
    console.error(err)
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  if (competitionId) getCompetitionInfo()
  else { ElMessage.error('赛事ID不存在'); router.push('/') }
})
</script>

<style scoped>
.register-page { min-height: 100vh; background-color: #f5f7fa; }
.logo { font-size: 20px; font-weight: bold; color: #409eff; display: flex; align-items: center; gap: 8px; cursor: pointer; }
.nav { display: flex; gap: 32px; }
.nav-item { font-size: 16px; color: #606266; transition: all 0.3s; text-decoration: none; padding-bottom: 4px; border-bottom: 2px solid transparent; }
.nav-item:hover, .nav-item.active { color: #409eff; border-bottom-color: #409eff; }
.register-content { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
.register-card { background: #fff; border-radius: 12px; padding: 40px; }
.page-title { text-align: center; font-size: 24px; font-weight: 600; color: #303133; margin: 0 0 24px 0; }
.competition-info { background: #f5f7fa; border-radius: 8px; padding: 20px; margin-bottom: 30px; }
.competition-info p { margin: 8px 0; font-size: 15px; color: #606266; }
.competition-info p span { color: #909399; }
.register-form { margin-bottom: 40px; }
.action-row { display: flex; justify-content: center; gap: 20px; }
</style>