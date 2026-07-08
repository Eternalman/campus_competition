<template>
  <div class="competition-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="left-buttons">
        <el-button type="primary" @click="openAddDialog">+ 新增</el-button>
        <el-button 
          type="danger" 
          @click="batchDelete" 
          :disabled="selectedRows.length === 0"
        >
          批量删除
          <span v-if="selectedRows.length > 0" class="selected-count">({{ selectedRows.length }})</span>
        </el-button>
      </div>
      <div class="search-box">
        <el-input v-model="searchForm.title" placeholder="请输入赛事名称搜索" clearable style="width: 250px">
          <template #append>
            <el-button @click="getCompetitionList" :icon="Search" />
          </template>
        </el-input>
      </div>
    </div>

    <!-- 赛事列表表格 -->
    <el-table 
      :data="competitionList" 
      border 
      stripe 
      v-loading="loading"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="id" label="序号" width="80" />
      <el-table-column prop="title" label="赛事标题" min-width="200" />
      <el-table-column prop="level" label="等级" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.level === 'school'">校级</el-tag>
          <el-tag v-else-if="row.level === 'city'" type="success">市级</el-tag>
          <el-tag v-else-if="row.level === 'province'" type="warning">省级</el-tag>
          <el-tag v-else type="danger">国家级</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="报名时间" width="180">
        <template #default="{ row }">
          {{ $formatTime(row.registration_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="organizer" label="组织方" width="150" />
      <el-table-column label="竞赛时间" width="180">
        <template #default="{ row }">
          {{ $formatTime(row.competition_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="location" label="竞赛地点" width="150" />
      <el-table-column prop="description" label="赛事简介" min-width="200" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'draft'" type="info">草稿</el-tag>
          <el-tag v-else-if="row.status === 'published'" type="success">已发布</el-tag>
          <el-tag v-else type="danger">已结束</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.size"
      :total="pagination.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="getCompetitionList"
      @current-change="getCompetitionList"
      style="margin-top: 20px; justify-content: flex-end"
    />

    <!-- 新增/编辑赛事弹窗（同一个弹窗复用） -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑赛事' : '新增赛事'"
      width="80%"
      @close="resetForm"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="赛事标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入" />
        </el-form-item>

        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择" style="width: 100%">
            <el-option
              v-for="item in categoryOptions"
              :key="item?.id || Math.random()"
              :label="item?.name || '未知分类'"
              :value="item?.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="封面" prop="cover">
          <el-upload
            class="cover-uploader"
            action="/api/competitions/upload-cover/"
            :headers="uploadHeaders"
            :show-file-list="false"
            :on-success="handleCoverSuccess"
            :before-upload="beforeCoverUpload"
          >
            <div v-if="form.cover" class="cover-preview">
              <!-- 编辑时封面正常显示，拼接完整地址 -->
              <img
                :src="form.cover"
                class="cover-image" 
              />
            </div>
            <div v-else class="upload-placeholder">
              <el-icon><Document /></el-icon>
              <div>请选择要上传的图片</div>
            </div>
          </el-upload>
        </el-form-item>

        <el-form-item label="赛事简介" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入" />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="等级" prop="level">
              <el-select v-model="form.level" placeholder="请选择" style="width: 100%">
                <el-option label="校级" value="school" />
                <el-option label="市级" value="city" />
                <el-option label="省级" value="province" />
                <el-option label="国家级" value="national" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="报名时间" prop="registration_time">
              <el-date-picker
                v-model="form.registration_time"
                type="datetime"
                placeholder="请输入"
                style="width: 100%"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="组织方" prop="organizer">
              <el-input v-model="form.organizer" placeholder="请输入" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="竞赛时间" prop="competition_time">
              <el-date-picker
                v-model="form.competition_time"
                type="datetime"
                placeholder="请输入"
                style="width: 100%"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="竞赛地点" prop="location">
              <el-input v-model="form.location" placeholder="请输入" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" placeholder="请选择" style="width: 100%">
                <el-option label="草稿" value="draft" />
                <el-option label="已发布" value="published" />
                <el-option label="已结束" value="ended" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="评委" prop="judges">
          <el-select v-model="form.judges" multiple placeholder="请选择评委（至少选择一个）" style="width: 100%">
            <el-option
              v-for="item in judgeOptions"
              :key="item.id"
              :label="item.nickname || item.username"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Search } from '@element-plus/icons-vue'
import axios from 'axios'

// TODO：建议将直接 axios 调用迁移到 @/utils/request 工具模块，
// 该模块已封装 token 自动注入、统一错误处理和响应数据解包，
// 可减少重复代码并保持与项目其他页面一致。

// 获取当前登录用户角色
const currentUser = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('admin_userInfo') || '{}')
  } catch {
    return { role: 'admin' }
  }
})

const isAdmin = computed(() => currentUser.value.role === 'admin')

// ========== 基础数据定义 ==========
const loading = ref(false)
const submitLoading = ref(false)
// 弹窗相关（新增/编辑复用）
const dialogVisible = ref(false)
const isEdit = ref(false) // 标记是新增还是编辑
const editId = ref(null) // 编辑的赛事ID
const formRef = ref()
const competitionList = ref([])
const categoryOptions = ref([])
const judgeOptions = ref([])
const selectedRows = ref([]) // 批量删除选中的行

// 搜索表单
const searchForm = ref({
  title: ''
})

// 分页
const pagination = ref({
  page: 1,
  size: 10,
  total: 0
})

// 表单数据（新增/编辑复用）
const form = ref({
  title: '',
  category: null,
  cover: '',
  description: '',
  level: '',
  registration_time: '',
  organizer: '',
  competition_time: '',
  location: '',
  status: '',
  judges: []
})

// 表单校验规则
const formRules = {
  title: [{ required: true, message: '请输入赛事标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  judges: [{ required: true, type: 'array', min: 1, message: '请至少选择一个评委', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

// 上传请求头
const uploadHeaders = ref({
  Authorization: `Bearer ${localStorage.getItem('admin_token') || ''}`
})

// ========== 核心方法 ==========
// 获取赛事列表
const getCompetitionList = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/competitions/', {
      headers: uploadHeaders.value,
      params: {
        page: pagination.value.page,
        page_size: pagination.value.size,
        title: searchForm.value.title
      }
    })
    competitionList.value = Array.isArray(res.data?.results) ? res.data.results : Array.isArray(res.data) ? res.data : []
    pagination.value.total = res.data?.count || res.data?.length || 0
  } catch (err) {
    competitionList.value = []
    pagination.value.total = 0
    ElMessage.error('获取赛事列表失败')
    console.error('赛事列表报错：', err)
  } finally {
    loading.value = false
  }
}

// 获取分类下拉选项
const getCategoryOptions = async () => {
  try {
    const res = await axios.get('/api/category-options/', {
      headers: uploadHeaders.value
    })
    categoryOptions.value = Array.isArray(res.data?.results) ? res.data.results : Array.isArray(res.data) ? res.data : []
  } catch (err) {
    categoryOptions.value = []
    console.error('分类接口报错：', err)
    ElMessage.error('获取分类列表失败')
  }
}

// 获取评委下拉选项
const getJudgeOptions = async () => {
  try {
    const res = await axios.get('/api/users/', {
      headers: uploadHeaders.value
    })
    const users = Array.isArray(res.data?.results) ? res.data.results : Array.isArray(res.data) ? res.data : []
    judgeOptions.value = users.filter(user => user.role === 'judge')
  } catch (err) {
    judgeOptions.value = []
    console.error('评委接口报错：', err)
    ElMessage.error('获取评委列表失败')
  }
}

// 打开新增弹窗
const openAddDialog = () => {
  isEdit.value = false
  editId.value = null
  dialogVisible.value = true
  getCategoryOptions()
  getJudgeOptions()
}

// 【核心修复】打开编辑弹窗（必须是顶层函数，模板可访问）
const openEditDialog = (row) => {
  console.log('编辑按钮点击，当前赛事数据：', row)
  isEdit.value = true
  editId.value = row.id
  // 表单数据回填（深拷贝，避免修改原数据）
  form.value = {
    title: row.title || '',
    category: row.category || null,
    cover: row.cover || '',
    description: row.description || '',
    level: row.level || '',
    registration_time: row.registration_time || '',
    organizer: row.organizer || '',
    competition_time: row.competition_time || '',
    location: row.location || '',
    status: row.status || '',
    judges: row.judges || []
  }
  dialogVisible.value = true
  // 打开弹窗时加载分类和评委选项，确保下拉框能正常选中
  getCategoryOptions()
  getJudgeOptions()
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields?.()
  form.value = {
    title: '',
    category: null,
    cover: '',
    description: '',
    level: '',
    registration_time: '',
    organizer: '',
    competition_time: '',
    location: '',
    status: '',
    judges: []
  }
  isEdit.value = false
  editId.value = null
}

// 封面上传前校验
const beforeCoverUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isImage) {
    ElMessage.error('只能上传图片文件！')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过2MB！')
    return false
  }
  return true
}

// 封面上传成功回调
const handleCoverSuccess = (res) => {
  if (res.code === 200) {
    const fullUrl = res.data.url
    const relativePath = fullUrl.replace(/^https?:\/\/[^/]+/, '')
    form.value.cover = relativePath
    ElMessage.success('封面上传成功')
  } else {
    ElMessage.error(res.msg || '封面上传失败')
  }
}

// 提交表单（新增/编辑共用）
const handleSubmit = async () => {
  // 表单验证：必须先确保 formRef 存在且验证通过再继续
  if (!formRef.value) {
    ElMessage.error('表单未正确加载')
    return
  }
  try {
    await formRef.value.validate()
  } catch {
    // validate() 验证失败时会 reject，终止提交流程
    return
  }
  submitLoading.value = true
  try {
    // 过滤只读字段，只提交需要的内容
    const submitData = {
      title: form.value.title,
      category: form.value.category,
      cover: form.value.cover || '', // 空值兜底
      description: form.value.description || '',
      level: form.value.level || '',
      registration_time: form.value.registration_time || '',
      organizer: form.value.organizer || '',
      competition_time: form.value.competition_time || '',
      location: form.value.location || '',
      status: form.value.status,
      judges: form.value.judges
    }

    if (isEdit.value) {
      // 编辑：PUT请求
      await axios.put(
        `/api/competitions/${editId.value}/`,
        submitData,
        { headers: uploadHeaders.value }
      )
      ElMessage.success('编辑赛事成功')
    } else {
      // 新增：POST请求
      await axios.post(
        '/api/competitions/',
        submitData,
        { headers: uploadHeaders.value }
      )
      ElMessage.success('新增赛事成功')
    }

    // 关闭弹窗、重置表单、刷新列表
    dialogVisible.value = false
    resetForm()
    getCompetitionList()
  } catch (err) {
    console.error('提交报错详情：', err.response?.data)
    ElMessage.error(isEdit.value ? '编辑赛事失败' : '新增赛事失败')
  } finally {
    submitLoading.value = false
  }
}

// 表格选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 批量删除
const batchDelete = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的赛事')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 个赛事吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 使用批量删除接口
    const ids = selectedRows.value.map(row => row.id)
    await axios.post(
      '/api/competitions/batch-delete/',
      { ids },
      { headers: uploadHeaders.value }
    )

    ElMessage.success('批量删除成功')
    selectedRows.value = []
    getCompetitionList()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('批量删除失败')
      console.error(err)
    }
  }
}

// 单个删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该赛事吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await axios.delete(`/api/competitions/${row.id}/`, {
      headers: uploadHeaders.value
    })
    ElMessage.success('删除成功')
    getCompetitionList()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(err)
    }
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  getCompetitionList()
  getCategoryOptions()
  getJudgeOptions()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.left-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}
.selected-count {
  margin-left: 4px;
  font-size: 14px;
  color: #fff;
}
.search-box {
  display: flex;
  align-items: center;
}
.cover-uploader {
  width: 100%;
}
.upload-placeholder {
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  background-color: #fafafa;
  height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #606266;
}
.upload-placeholder .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.cover-preview {
  width: 100%;
  height: 180px;
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
}
.cover-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
</style>