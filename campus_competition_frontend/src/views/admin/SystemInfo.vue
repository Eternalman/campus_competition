<template>
  <div class="system-page">
    <div class="info-card">
      <h2 class="card-title">系统信息</h2>
      <el-descriptions :column="2" border v-loading="loading">
        <el-descriptions-item label="系统名称">{{ systemInfo.system_name }}</el-descriptions-item>
        <el-descriptions-item label="版本信息">{{ systemInfo.version }}</el-descriptions-item>
        <el-descriptions-item label="操作系统">{{ systemInfo.os }}</el-descriptions-item>
        <el-descriptions-item label="系统平台">{{ systemInfo.platform }}</el-descriptions-item>
        <el-descriptions-item label="CPU核数">{{ systemInfo.cpu_core }}</el-descriptions-item>
        <el-descriptions-item label="处理器">{{ systemInfo.cpu_processor }}</el-descriptions-item>
        <el-descriptions-item label="CPU负载">{{ systemInfo.cpu_load }}</el-descriptions-item>
        <el-descriptions-item label="系统内存">{{ systemInfo.total_memory }}</el-descriptions-item>
        <el-descriptions-item label="内存使用">{{ systemInfo.used_memory }}</el-descriptions-item>
        <el-descriptions-item label="内存利用率">
          <el-progress :percentage="memoryPercent" :color="memoryColor" />
        </el-descriptions-item>
        <el-descriptions-item label="系统语言">{{ systemInfo.system_language }}</el-descriptions-item>
        <el-descriptions-item label="MySQL版本">{{ systemInfo.mysql_version }}</el-descriptions-item>
        <el-descriptions-item label="Nginx版本">{{ systemInfo.nginx_version }}</el-descriptions-item>
        <el-descriptions-item label="系统时区">{{ systemInfo.timezone }}</el-descriptions-item>
      </el-descriptions>
      <div class="refresh-btn">
        <el-button type="primary" :icon="Refresh" @click="getInfo">刷新信息</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const systemInfo = ref({})

const memoryPercent = computed(() => {
  if (!systemInfo.value.memory_usage) return 0
  return parseInt(systemInfo.value.memory_usage)
})

const memoryColor = computed(() => {
  const p = memoryPercent.value
  if (p < 60) return '#67c23a'
  if (p < 80) return '#e6a23c'
  return '#f56c6c'
})

const getInfo = async () => {
  loading.value = true
  try {
    systemInfo.value = await request.get('/system/info/')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  getInfo()
})
</script>

<style scoped>
.system-page { background: #fff; padding: 20px; border-radius: 4px; min-height: calc(100vh - 140px); }
.info-card { padding: 20px; }
.card-title { font-size: 20px; color: #303133; margin: 0 0 30px; padding-bottom: 15px; border-bottom: 1px solid #ebeef5; }
.refresh-btn { margin-top: 30px; text-align: center; }
</style>