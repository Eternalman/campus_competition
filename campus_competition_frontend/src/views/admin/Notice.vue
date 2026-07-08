<template>
  <div class="notice-page">
    <div class="page-header">
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        新增公告
      </el-button>
    </div>
    <div class="table-container">
      <el-table :data="noticeList" border stripe>
        <el-table-column prop="title" label="标题" width="200" />
        <el-table-column prop="content" label="内容" min-width="350">
          <template #default="{ row }">
            <div class="content-cell">{{ row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="pagination">
      <span class="total">共 {{ pagination.total }} 条数据</span>
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        @size-change="fetchNoticeList"
        @current-change="fetchNoticeList"
      />
    </div>

    <!-- 新增/编辑公告对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="公告标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入公告标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="公告内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="请输入公告内容" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { formatTime } from '@/utils/format'

const noticeList = ref([])
const pagination = ref({ page: 1, size: 10, total: 0 })
const dialogVisible = ref(false)
const dialogTitle = ref('')
const submitLoading = ref(false)
const formRef = ref(null)

const form = reactive({ id: null, title: '', content: '' })

const formRules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }]
}

const fetchNoticeList = async () => {
  try {
    const res = await request.get('/notices/', {
      params: { page: pagination.value.page, page_size: pagination.value.size }
    })
    noticeList.value = res.results || res
    pagination.value.total = res.count || res.length
  } catch (err) {
    ElMessage.error('获取公告列表失败')
  }
}

const showAddDialog = () => {
  dialogTitle.value = '新增公告'
  Object.assign(form, { id: null, title: '', content: '' })
  if (formRef.value) formRef.value.clearValidate()
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  dialogTitle.value = '编辑公告'
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (form.id) {
          await request.put(`/notices/${form.id}/`, form)
          ElMessage.success('编辑成功')
        } else {
          await request.post('/notices/', form)
          ElMessage.success('新增成功')
        }
        dialogVisible.value = false
        fetchNoticeList()
      } catch (err) {
        ElMessage.error('操作失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该公告吗？', '提示', { type: 'warning' }).then(async () => {
    try {
      await request.delete(`/notices/${row.id}/`)
      ElMessage.success('删除成功')
      fetchNoticeList()
    } catch (err) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchNoticeList()
})
</script>

<style scoped>
.notice-page {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  min-height: calc(100vh - 140px);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.table-container {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}
.table-container :deep(.el-table) {
  border-radius: 8px;
}
.content-cell {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
  color: #606266;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 24px;
  gap: 20px;
}
.total {
  color: #606266;
  font-size: 14px;
}
</style>