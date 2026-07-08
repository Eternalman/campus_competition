<template>
  <div class="registration-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="left-buttons">
        <el-button type="danger" @click="batchDelete">批量删除</el-button>
      </div>
      <div class="search-box">
        <el-select 
          v-model="searchForm.competition" 
          placeholder="选择赛事分类" 
          clearable 
          style="width: 200px; margin-right: 10px;"
          @change="handleSearch"
        >
          <el-option 
            v-for="comp in competitionList" 
            :key="comp.id" 
            :label="comp.title" 
            :value="comp.id" 
          />
        </el-select>
        <el-input 
          v-model="searchForm.keyword" 
          placeholder="请输入姓名/赛事名称搜索" 
          clearable 
          style="width: 300px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #append>
            <el-button @click="handleSearch" :icon="Search" />
          </template>
        </el-input>
      </div>
    </div>

    <!-- 报名列表表格 -->
    <el-table 
      :data="registrationList" 
      border 
      stripe 
      v-loading="loading" 
      @selection-change="handleSelectionChange"
      style="width: 100%"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="id" label="序号" width="70" />
      <el-table-column prop="username" label="用户" width="100" show-overflow-tooltip />
      <el-table-column prop="competition_title" label="赛事名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="name" label="报名姓名" width="100" show-overflow-tooltip />
      <el-table-column prop="id_card" label="身份证号" width="180" />
      <el-table-column prop="school" label="所属学校" width="130" show-overflow-tooltip />
      <el-table-column prop="status_display" label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'normal'" type="primary" size="small">正常</el-tag>
          <el-tag v-else-if="row.status === 'canceled'" type="success" size="small">已取消</el-tag>
          <el-tag v-else type="info" size="small">已完成</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="score" label="成绩" width="90">
        <template #default="{ row }">
          <span v-if="row.score" style="color: #67c23a; font-weight: bold;">{{ row.score }}</span>
          <span v-else style="color: #909399;">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" width="180" show-overflow-tooltip />
      <!-- ✅ 新增：附件列 -->
      <el-table-column label="附件" width="100">
        <template #default="{ row }">
          <template v-if="row.file_url">
            <el-button 
              v-if="isImage(row.file_url) || isVideo(row.file_url)" 
              type="primary" 
              link 
              size="small" 
              @click="previewOrDownload(row)"
            >
              {{ isImage(row.file_url) ? '预览' : '播放' }}
            </el-button>
            <el-button 
              type="primary" 
              link 
              size="small" 
              @click="downloadFile(row.file_url)"
            >
              下载
            </el-button>
          </template>
          <span v-else style="color: #909399;">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openScoreDialog(row)">成绩</el-button>
          <el-button 
            type="warning" 
            link 
            size="small" 
            @click="handleCancel(row)"
            :disabled="row.status === 'canceled'"
          >取消</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <!-- ✅ 新增：图片预览弹窗 -->
    <el-dialog v-model="imageDialogVisible" title="图片预览" width="60%" top="5vh">
      <div style="text-align: center;">
        <el-image
          :src="currentPreviewUrl"
          fit="contain"
          style="max-width: 100%; max-height: 70vh;"
          :preview-src-list="[currentPreviewUrl]"
          :initial-index="0"
          preview-teleported
        />
      </div>
    </el-dialog>

    <!-- ✅ 新增：视频预览弹窗 -->
    <el-dialog v-model="videoDialogVisible" title="视频预览" width="70%" top="5vh">
      <div style="text-align: center;">
        <video
          :src="currentPreviewUrl"
          controls
          style="width: 100%; max-height: 70vh;"
        >
          您的浏览器不支持视频播放
        </video>
      </div>
    </el-dialog>
    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.size"
      :total="pagination.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="getRegistrationList"
      @current-change="getRegistrationList"
      style="margin-top: 20px; justify-content: flex-end"
    />

    <!-- 成绩录入弹窗 -->
    <el-dialog v-model="scoreDialogVisible" title="录入赛事成绩" width="500px">
      <el-form :model="scoreForm" label-width="100px">
        <el-form-item label="赛事名称">
          <span>{{ scoreForm.competition_title }}</span>
        </el-form-item>
        <el-form-item label="报名姓名">
          <span>{{ scoreForm.name }}</span>
        </el-form-item>
        <el-form-item label="赛事成绩" prop="score">
          <el-input v-model="scoreForm.score" placeholder="请输入成绩" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scoreDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="scoreLoading" @click="submitScore">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import axios from 'axios'

// TODO：建议将直接 axios 调用迁移到 @/utils/request 工具模块，
// 该模块已封装 token 自动注入和统一错误处理。

// 基础数据
const loading = ref(false)
const scoreLoading = ref(false)
const scoreDialogVisible = ref(false)
const registrationList = ref([])
const selectedIds = ref([])
const competitionList = ref([])


// ✅ 新增：预览相关变量
const imageDialogVisible = ref(false)
const videoDialogVisible = ref(false)
const currentPreviewUrl = ref('')

// ✅ 新增：判断文件类型
const isImage = (url) => {
  if (!url) return false
  const ext = url.split('.').pop().toLowerCase()
  return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)
}

const isVideo = (url) => {
  if (!url) return false
  const ext = url.split('.').pop().toLowerCase()
  return ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'].includes(ext)
}

// ✅ 新增：预览图片
const previewImage = (url) => {
  currentPreviewUrl.value = url
  imageDialogVisible.value = true
}

// ✅ 新增：预览视频
const previewVideo = (url) => {
  currentPreviewUrl.value = url
  videoDialogVisible.value = true
}

// ✅ 新增：下载文件
const downloadFile = (url) => {
  if (!url) {
    ElMessage.warning('无附件可下载')
    return
  }
  const link = document.createElement('a')
  link.href = url
  link.target = '_blank'
  link.download = url.split('/').pop()
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('开始下载...')
}

// ✅ 新增：统一预览或下载
const previewOrDownload = (row) => {
  const url = row.file_url
  if (!url) return
  if (isImage(url)) {
    previewImage(url)
  } else if (isVideo(url)) {
    previewVideo(url)
  } else {
    downloadFile(url)
  }
}



// 搜索表单
const searchForm = ref({
  keyword: '',
  competition: null
})

// 分页
const pagination = ref({
  page: 1,
  size: 10,
  total: 0
})

// 成绩表单
const scoreForm = ref({
  id: null,
  competition_title: '',
  name: '',
  score: ''
})

// 请求头
const requestHeaders = {
  // Authorization: `Bearer ${localStorage.getItem('token') || ''}`
  Authorization: `Bearer ${localStorage.getItem('admin_token') || ''}`
}

// 获取赛事列表
const getCompetitionList = async () => {
  try {
    const res = await axios.get('/api/competitions/', {
      headers: requestHeaders,
      params: { page_size: 1000 }
    })
    competitionList.value = Array.isArray(res.data?.results) ? res.data.results : Array.isArray(res.data) ? res.data : []
  } catch (err) {
    console.error('获取赛事列表失败:', err)
  }
}

// 获取报名列表
const getRegistrationList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.size,
      search: searchForm.value.keyword
    }
    if (searchForm.value.competition) {
      params.competition = searchForm.value.competition
    }
    const res = await axios.get('/api/registrations/', {
      headers: requestHeaders,
      params
    })
    registrationList.value = Array.isArray(res.data?.results) ? res.data.results : Array.isArray(res.data) ? res.data : []
    pagination.value.total = res.data?.count || res.data?.length || 0
  } catch (err) {
    registrationList.value = []
    pagination.value.total = 0
    ElMessage.error('获取报名列表失败')
    console.error(err)
  } finally {
    loading.value = false
  }
}

// 多选
const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

// 打开成绩录入弹窗
const openScoreDialog = (row) => {
  scoreForm.value = {
    id: row.id,
    competition_title: row.competition_title,
    name: row.name,
    score: row.score || ''
  }
  scoreDialogVisible.value = true
}

// 提交成绩
const submitScore = async () => {
  if (!scoreForm.value.score) {
    ElMessage.warning('请输入成绩')
    return
  }
  scoreLoading.value = true
  try {
    await axios.post(
      `/api/registrations/${scoreForm.value.id}/set-score/`,
      { score: scoreForm.value.score },
      { headers: requestHeaders }
    )
    ElMessage.success('成绩录入成功')
    scoreDialogVisible.value = false
    getRegistrationList()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '成绩录入失败')
    console.error(err)
  } finally {
    scoreLoading.value = false
  }
}

// 取消报名
const handleCancel = async (row) => {
  try {
    await ElMessageBox.confirm('确定要取消该报名吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await axios.post(
      `/api/registrations/${row.id}/cancel/`,
      {},
      { headers: requestHeaders }
    )
    ElMessage.success('取消成功')
    getRegistrationList()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '取消失败')
      console.error(err)
    }
  }
}

// 单个删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该报名记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await axios.delete(`/api/registrations/${row.id}/`, {
      headers: requestHeaders
    })
    ElMessage.success('删除成功')
    getRegistrationList()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(err)
    }
  }
}

// 批量删除
const batchDelete = () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的记录')
    return
  }
  ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 条记录吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      const promiseList = selectedIds.value.map(id => {
        return axios.delete(`/api/registrations/${id}/`, {
          headers: requestHeaders
        })
      })
      await Promise.all(promiseList)
      ElMessage.success('批量删除成功')
      getRegistrationList()
    } catch (err) {
      ElMessage.error('批量删除失败')
      console.error(err)
    }
  }).catch(() => {})
}

// 监听搜索条件变化
const handleSearch = () => {
  pagination.value.page = 1
  getRegistrationList()
}

onMounted(() => {
  getCompetitionList()
  getRegistrationList()
})
</script>

<style scoped>
.registration-page {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  min-height: calc(100vh - 140px);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.left-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}
.search-box {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
</style>