<template>
  <div class="message-page">
    <div class="toolbar">
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
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="content" label="内容" min-width="250" show-overflow-tooltip />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="email" label="Email" width="180" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const tableData = ref([])
const multipleSelection = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const getList = async () => {
  const res = await request.get('/messages/', { params: { page: currentPage.value, page_size: pageSize.value } })
  tableData.value = res.results || res
  total.value = res.count || res.length
}

const handleSelectionChange = (val) => {
  multipleSelection.value = val
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该留言吗？', '提示', { type: 'warning' }).then(async () => {
    await request.delete(`/messages/${row.id}/`)
    ElMessage.success('删除成功')
    getList()
  }).catch(() => {})
}

const handleBatchDelete = () => {
  ElMessageBox.confirm(`确定要删除选中的 ${multipleSelection.value.length} 条数据吗？`, '提示', { type: 'warning' }).then(async () => {
    for (const item of multipleSelection.value) {
      await request.delete(`/messages/${item.id}/`)
    }
    ElMessage.success('批量删除成功')
    getList()
  }).catch(() => {})
}

onMounted(() => getList())
</script>

<style scoped>
.message-page { background: #fff; padding: 20px; border-radius: 4px; min-height: calc(100vh - 140px); }
.toolbar { margin-bottom: 20px; }
.table-container { border: 1px solid #ebeef5; border-radius: 4px; }
.pagination { display: flex; justify-content: flex-end; align-items: center; margin-top: 20px; gap: 20px; }
.total { color: #606266; font-size: 14px; }
</style>