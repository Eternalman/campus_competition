<template>
  <div class="user-page">
    <div class="toolbar">
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>新增
      </el-button>
      <div class="toolbar-right">
        <el-input
          v-model="searchKeyword"
          placeholder="用户名"
          style="width: 250px"
          clearable
          @keyup.enter="getList"
        >
          <template #append>
            <el-button :icon="Search" @click="getList" />
          </template>
        </el-input>
      </div>
    </div>

    <div class="table-container">
      <el-table :data="tableData" style="width: 100%" border stripe>
        <el-table-column prop="id" label="序号" width="80" align="center" />
        <el-table-column label="头像" width="80" align="center">
          <template #default="{ row }">
            <el-avatar :size="40" :src="row.avatar || 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'" />
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="role" label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'judge' ? 'warning' : 'primary'" size="small">
              {{ row.role === 'admin' ? '管理员' : row.role === 'judge' ? '评委' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column label="操作" :width="isAdmin ? 150 : 80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="isAdmin" type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
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
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="600px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item :label="isEdit ? '新密码' : '密码'" prop="password" :required="!isEdit">
          <el-input v-model="formData.password" type="password" show-password :placeholder="isEdit ? '请输入新密码，留空则不修改' : '请输入密码'" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="formData.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="角色" prop="role" v-if="isAdmin">
          <el-select v-model="formData.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="评委" value="judge" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入手机号" />
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
import { Search, Plus } from '@element-plus/icons-vue'
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
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)

const formData = reactive({
  id: null,
  username: '',
  password: '',
  nickname: '',
  role: 'user',
  email: '',
  phone: ''
})

const formRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const getList = async () => {
  const params = { page: currentPage.value, page_size: pageSize.value, search: searchKeyword.value }
  const res = await request.get('/users/', { params })
  tableData.value = res.results || res
  total.value = res.count || res.length
}

const handleAdd = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(formData, row)
  formData.password = '' // 编辑时清空密码字段
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (isEdit.value) {
          // 编辑时，如果密码为空则不发送密码字段
          const submitData = { ...formData }
          if (!submitData.password) {
            delete submitData.password
          }
          await request.put(`/users/${formData.id}/`, submitData)
          ElMessage.success('编辑成功')
        } else {
          await request.post('/users/', formData)
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
  ElMessageBox.confirm('确定要删除该用户吗？', '提示', { type: 'warning' }).then(async () => {
    await request.delete(`/users/${row.id}/`)
    ElMessage.success('删除成功')
    getList()
  }).catch(() => {})
}

const resetForm = () => {
  Object.assign(formData, { id: null, username: '', password: '', nickname: '', role: 'user', email: '', phone: '' })
  if (formRef.value) formRef.value.clearValidate()
}

onMounted(() => getList())
</script>

<style scoped>
.user-page { 
  background: #fff; 
  padding: 24px; 
  border-radius: 8px; 
  min-height: calc(100vh - 140px); 
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}
.toolbar { 
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