<template>
  <div class="knowledge-base-page">
    <div class="page-header">
      <el-upload
        class="upload-area"
        drag
        multiple
        :action="uploadUrl"
        :headers="uploadHeaders"
        :accept="acceptTypes"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">
            支持 PDF、Word(.docx)、PPT(.pptx)、TXT、Markdown(.md)、CSV、Excel、图片(jpg/png) 格式
          </div>
        </template>
      </el-upload>
    </div>

    <div class="table-container">
      <el-table :data="documentList" border stripe v-loading="loading">
        <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100" align="center">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="处理状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'completed'" type="success" size="small">已完成</el-tag>
            <el-tag v-else-if="row.status === 'processing'" type="warning" size="small">
              <el-icon class="is-loading"><Loading /></el-icon> 处理中
            </el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
            <el-tag v-else type="info" size="small">已上传</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数" width="80" align="center" />
        <el-table-column label="学科来源" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.source }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'failed'"
              type="warning"
              link
              size="small"
              @click="handleReprocess(row)"
            >重试</el-button>
            <el-button
              type="danger"
              link
              size="small"
              @click="handleDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination">
      <span class="total">共 {{ total }} 条数据</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchDocumentList"
        @current-change="fetchDocumentList"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { formatTime } from '@/utils/format'

const documentList = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const uploadUrl = 'http://127.0.0.1:8000/api/rag/documents/'
const acceptTypes = '.txt,.pdf,.docx,.ppt,.pptx,.jpg,.png,.md,.csv,.xlsx,.xls'

const uploadHeaders = computed(() => {
  const token = localStorage.getItem('admin_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
})

// 格式化文件大小
function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return size.toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

// 上传前校验
function beforeUpload(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  const allowed = ['txt', 'pdf', 'docx', 'ppt', 'pptx', 'jpg', 'png', 'md', 'csv', 'xlsx', 'xls']
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的文件类型: .${ext}`)
    return false
  }
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

// 上传成功
function handleUploadSuccess(response) {
  ElMessage.success('文件上传成功，后台正在处理...')
  fetchDocumentList()
  // 5 秒后刷新状态
  setTimeout(() => fetchDocumentList(), 5000)
}

// 上传失败
function handleUploadError(err) {
  ElMessage.error('上传失败：' + (err.message || '未知错误'))
}

// 获取文档列表
async function fetchDocumentList() {
  loading.value = true
  try {
    const res = await request.get('/rag/documents/', {
      params: { page: page.value, page_size: pageSize.value },
    })
    documentList.value = res.results || []
    total.value = res.count || 0
  } catch (e) {
    ElMessage.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

// 重新处理
async function handleReprocess(row) {
  try {
    await request.post(`/rag/documents/${row.id}/reprocess/`)
    ElMessage.success('已重新提交处理')
    fetchDocumentList()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

// 删除文档
function handleDelete(row) {
  ElMessageBox.confirm(
    `确定要删除 "${row.original_name}" 吗？将同时删除文件和向量数据，不可恢复。`,
    '确认删除',
    { type: 'warning' }
  ).then(async () => {
    try {
      await request.delete(`/rag/documents/${row.id}/`)
      ElMessage.success('删除成功')
      fetchDocumentList()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchDocumentList()
})
</script>

<style scoped>
.knowledge-base-page {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}
.page-header {
  margin-bottom: 20px;
}
.upload-area {
  width: 100%;
}
.upload-icon {
  font-size: 48px;
  color: #409eff;
}
.upload-text {
  font-size: 14px;
  color: #606266;
  margin-top: 8px;
}
.upload-tip {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}
.table-container {
  margin-top: 20px;
}
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.total {
  color: #606266;
  font-size: 14px;
}
.is-loading {
  animation: rotating 1s linear infinite;
}
@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
