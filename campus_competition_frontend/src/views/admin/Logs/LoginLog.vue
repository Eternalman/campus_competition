<template>
  <div class="log-page">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <div class="left-buttons">
        <el-button type="primary" @click="getList">
          <el-icon><Refresh /></el-icon>刷新
        </el-button>
        <el-button 
          type="danger" 
          @click="batchDelete" 
          :disabled="selectedRows.length === 0"
        >
          批量删除
          <span v-if="selectedRows.length > 0" class="selected-count">({{ selectedRows.length }})</span>
        </el-button>
      </div>
      <div class="toolbar-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户名/IP地址"
          style="width: 250px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" />
          </template>
        </el-input>
      </div>
    </div>

    <!-- 日志表格 -->
    <div class="table-container">
      <el-table
        :data="tableData"
        style="width: 100%"
        border
        stripe
        v-loading="tableLoading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column prop="username" label="登录用户名" width="120" />
        <el-table-column prop="ip_address" label="登录IP地址" width="150" />
        <el-table-column 
          prop="status" 
          label="登录状态" 
          width="100"
        >
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fail_reason" label="失败原因" min-width="200" show-overflow-tooltip />
        <el-table-column prop="user_agent" label="浏览器/设备信息" min-width="300" show-overflow-tooltip />
        <el-table-column prop="login_time" label="登录时间" width="180" />
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <span class="total">共 {{ total }} 条日志</span>
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
        layout="prev, pager, next, jumper, ->, sizes, total"
        :page-sizes="[10, 20, 50, 100]"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

// 数据定义
const tableData = ref([])
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const tableLoading = ref(false)
const selectedRows = ref([])

// 表格选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1
  selectedRows.value = []
  getList()
}

// 页码变化
const handlePageChange = () => {
  selectedRows.value = []
  getList()
}

// 每页条数变化
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  selectedRows.value = []
  getList()
}

// 批量删除
const batchDelete = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的日志')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 条日志吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const ids = selectedRows.value.map(row => row.id)
    await request.post('/login-logs/batch-delete/', { ids })

    ElMessage.success('批量删除成功')
    selectedRows.value = []
    getList()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('批量删除失败')
      console.error(err)
    }
  }
}

// 获取登录日志列表
const getList = async () => {
  tableLoading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      limit: pageSize.value,
      search: searchKeyword.value
    }
    console.log('请求参数:', params)
    const res = await request.get('/login-logs/', { params })
    console.log('响应结果:', res)
    tableData.value = res.results || res
    total.value = res.count || res.length
  } catch (err) {
    ElMessage.error('获取登录日志失败：' + (err.message || '网络错误'))
    tableData.value = []
    total.value = 0
  } finally {
    tableLoading.value = false
  }
}

// 页面挂载时加载数据
onMounted(() => {
  getList()
})
</script>

<style scoped>
.log-page {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  min-height: calc(100vh - 140px);
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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
.toolbar-right {
  display: flex;
  gap: 10px;
}
.table-container {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 20px;
  gap: 20px;
}
.total {
  color: #606266;
  font-size: 14px;
}
</style>