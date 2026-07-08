<template>
  <div class="success-page">
    <!-- 成功提示 -->
    <div class="success-content">
      <div class="success-card">
        <div class="success-icon">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <h2 class="title">报名成功</h2>
        <p class="desc">资料已提交成功，感谢使用</p>
        <el-button type="primary" size="large" @click="goMyRegistrations">查看报名</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Trophy, CircleCheck } from '@element-plus/icons-vue'

const router = useRouter()
const goMyRegistrations = () => router.push('/profile/registrations')
</script>

<style scoped>
.success-page { min-height: 100vh; background-color: #f5f7fa; }
.logo { font-size: 20px; font-weight: bold; color: #409eff; display: flex; align-items: center; gap: 8px; cursor: pointer; }
.nav { display: flex; gap: 32px; }
.nav-item { font-size: 16px; color: #606266; transition: all 0.3s; text-decoration: none; padding-bottom: 4px; border-bottom: 2px solid transparent; }
.nav-item:hover, .nav-item.active { color: #409eff; border-bottom-color: #409eff; }
.success-content { max-width: 1400px; margin: 0 auto; padding: 100px 20px; display: flex; justify-content: center; }
.success-card { text-align: center; background: #fff; border-radius: 12px; padding: 60px 80px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.success-icon { font-size: 80px; color: #67c23a; margin-bottom: 20px; }
.title { font-size: 28px; font-weight: 600; color: #303133; margin: 0 0 12px 0; }
.desc { font-size: 16px; color: #909399; margin: 0 0 30px 0; }
</style>