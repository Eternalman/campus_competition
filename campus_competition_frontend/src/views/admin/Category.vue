<template>
  <div class="category-page">
    <div class="toolbar">
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>新增
      </el-button>
      <el-button type="danger" :disabled="multipleSelection.length === 0" @click="handleBatchDelete">
        <el-icon><Delete /></el-icon>批量删除
      </el-button>
    </div>

    <div class="table-container">
      <el-table
        :data="tableData"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        border
        stripe
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column prop="name" label="分类名称" min-width="200" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination">
      <span class="total">共 {{ total }} 条数据</span>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        @current-change="getList"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑分类' : '新增分类'"
      width="500px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入分类名称" />
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'


// 获取当前登录用户角色
const currentUser = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('admin_userInfo') || '{}')
  } catch {
    return { role: 'admin' }
  }
})

const isAdmin = computed(() => currentUser.value.role === 'admin')


const tableData = ref([])
const multipleSelection = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)

const formData = reactive({
  id: null,
  name: ''
})

const formRules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }]
}

const getList = async () => {
  const res = await request.get('/categories/')
  tableData.value = res.results || res
  total.value = res.count || res.length
}

const handleSelectionChange = (val) => {
  multipleSelection.value = val
}

const handleAdd = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(formData, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (isEdit.value) {
          await request.put(`/categories/${formData.id}/`, formData)
          ElMessage.success('编辑成功')
        } else {
          await request.post('/categories/', formData)
          ElMessage.success('新增成功')
        }
        dialogVisible.value = false
        getList()
      } finally {
        submitLoading.value = false
      }
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该分类吗？', '提示', { type: 'warning' }).then(async () => {
    await request.delete(`/categories/${row.id}/`)
    ElMessage.success('删除成功')
    getList()
  }).catch(() => {})
}

const handleBatchDelete = () => {
  ElMessageBox.confirm(`确定要删除选中的 ${multipleSelection.value.length} 条数据吗？`, '提示', { type: 'warning' }).then(async () => {
    for (const item of multipleSelection.value) {
      await request.delete(`/categories/${item.id}/`)
    }
    ElMessage.success('批量删除成功')
    getList()
  }).catch(() => {})
}

const resetForm = () => {
  Object.assign(formData, { id: null, name: '' })
  if (formRef.value) formRef.value.clearValidate()
}

onMounted(() => {
  getList()
})
</script>

<style scoped>
.category-page {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  min-height: calc(100vh - 140px);
}
.toolbar { display: flex; justify-content: space-between; margin-bottom: 20px; }
.table-container { border: 1px solid #ebeef5; border-radius: 4px; }
.pagination { display: flex; justify-content: flex-end; align-items: center; margin-top: 20px; gap: 20px; }
.total { color: #606266; font-size: 14px; }
</style>