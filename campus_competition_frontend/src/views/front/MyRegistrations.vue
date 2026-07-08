<template>
  <div class="my-registrations-page">
    <el-table :data="registrationList" border stripe v-loading="loading">
      <el-table-column prop="id" label="序号" width="80" />
      <el-table-column prop="competition_title" label="赛事名称" min-width="200" />
      <el-table-column prop="name" label="报名姓名" width="120" />
      <el-table-column prop="school" label="所属学校" width="150" />
      <el-table-column prop="status_display" label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'normal'" type="primary">正常</el-tag>
          <el-tag v-else-if="row.status === 'canceled'" type="info">已取消</el-tag>
          <el-tag v-else type="success">已完成</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="score" label="成绩" width="120" />
      <el-table-column prop="created_at" label="报名时间" width="180" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="goDetail(row.competition)">查看赛事</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const router = useRouter()
const loading = ref(false)
const registrationList = ref([])

// 获取我的报名列表
const getMyRegistrations = async () => {
  loading.value = true
  try {
    const res = await request.get('/registrations/my/')
    registrationList.value = res
  } catch (err) {
    ElMessage.error('获取报名列表失败')
    console.error(err)
  } finally {
    loading.value = false
  }
}

// 跳转赛事详情
const goDetail = (competitionId) => router.push(`/competition/${competitionId}`)

onMounted(() => getMyRegistrations())
</script>

<style scoped>
.my-registrations-page { padding: 10px 0; }
</style>