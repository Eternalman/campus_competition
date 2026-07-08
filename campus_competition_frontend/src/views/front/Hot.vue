<template>
  <div class="hot-page">
    <!-- 热门列表 -->
    <div class="hot-content">
      <div class="page-title">
        <h2>🔥 热门推荐</h2>
        <p>按浏览次数排序</p>
      </div>
      
      <!-- 加载提示 -->
      <div class="loading-wrap" v-if="loading">
        <el-skeleton :rows="5" animated />
      </div>

      <div class="list-content" v-else>
        <!-- ✅ 修复1：v-for 加上 index，变量名改为 competitionList -->
        <div v-for="(item, index) in competitionList" :key="item.id" class="competition-card" @click="goDetail(item)">
          <div class="card-rank" :class="'rank-' + (index + 1)">
            {{ index + 1 }}
          </div>
          <div class="card-img">
            <img 
              :src="item.cover || getPlaceholderImage(item.id)" 
              :alt="item.title" 
              class="card-image"
              @error="e => e.target.src=getPlaceholderImage(item.id)"
            />
          </div>
          <div class="card-info">
            <h3 class="card-title">{{ item.title }}</h3>
            <p class="card-meta">
              <el-tag v-if="item.level === 'school'" size="small">{{ getLevelText(item.level) }}</el-tag>
              <el-tag v-else-if="item.level === 'city'" size="small" type="success">{{ getLevelText(item.level) }}</el-tag>
              <el-tag v-else-if="item.level === 'province'" size="small" type="warning">{{ getLevelText(item.level) }}</el-tag>
              <el-tag v-else size="small" type="danger">{{ getLevelText(item.level) }}</el-tag>
              <span>{{ item.organizer || '未知组织方' }}</span>
              <span class="view-count">{{ item.view_count || 0 }} 次浏览</span>
            </p>
          </div>
        </div>
      </div>
      
      <!-- 空数据提示 -->
      <el-empty v-if="!loading && competitionList.length === 0" description="暂无赛事数据" />

      <div class="pagination" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          @current-change="getHotCompetitions"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElSkeleton, ElTag } from 'element-plus'
import request from '@/utils/request'
import { useRouter } from 'vue-router'

const router = useRouter()

// ✅ 修复2：统一变量名
const competitionList = ref([])
const currentPage = ref(1)
const pageSize = ref(8)
const total = ref(0)
const loading = ref(false)

// 等级文本转换
const getLevelText = (level) => {
  const levelMap = {
    school: '校级',
    city: '市级',
    province: '省级',
    national: '国家级'
  }
  return levelMap[level] || '未知等级'
}

const goDetail = (item) => {
  router.push(`/competition/${item.id}`)
}

// 生成唯一的占位图URL，避免重复
const getPlaceholderImage = (id) => {
  return `https://picsum.photos/400/200?random=${id || Date.now()}`
}

// ✅ 修复3：统一函数名，修复变量名
const getHotCompetitions = async () => {
  loading.value = true
  try {
    const res = await request.get('/competitions/', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        // 按浏览量从高到低排序
        sort: 'hot'
      }
    })
    competitionList.value = res.results || res || []
    total.value = res.count || res.length || 0
  } catch (err) {
    ElMessage.error('获取热门赛事失败')
    console.error(err)
    competitionList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  getHotCompetitions()
})
</script>

<style scoped>
.hot-page { min-height: 100vh; background-color: #f5f7fa; }
.logo { font-size: 20px; font-weight: bold; color: #409eff; display: flex; align-items: center; gap: 8px; }
.nav { display: flex; gap: 30px; }
.nav-item { font-size: 16px; color: #606266; transition: color 0.3s; text-decoration: none; }
.nav-item:hover, .nav-item.active { color: #409eff; }
.hot-content { max-width: 1400px; margin: 0 auto; padding: 30px 20px; }
.page-title { margin-bottom: 30px; text-align: center; }
.page-title h2 { font-size: 32px; color: #303133; margin: 0 0 10px; }
.page-title p { font-size: 16px; color: #909399; margin: 0; }
.list-content { display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; }
.competition-card { background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.1); position: relative; transition: transform 0.3s; cursor: pointer; }
.competition-card:hover { transform: translateY(-5px); }
.card-rank { position: absolute; top: 15px; left: 15px; width: 36px; height: 36px; background: #909399; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; z-index: 10; }
.card-rank.rank-1 { background: linear-gradient(135deg, #ffd700, #ffb800); }
.card-rank.rank-2 { background: linear-gradient(135deg, #c0c0c0, #a0a0a0); }
.card-rank.rank-3 { background: linear-gradient(135deg, #cd7f32, #b06c2a); }
.card-img { width: 100%; height: 200px; overflow: hidden; }
.card-image { width: 100%; height: 100%; object-fit: cover; }
.card-info { padding: 15px; }
.card-title { font-size: 16px; font-weight: 500; margin-bottom: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { display: flex; justify-content: space-between; font-size: 12px; color: #909399; flex-wrap: wrap; gap: 5px; }
.view-count { color: #f56c6c; font-weight: bold; }
.pagination { display: flex; justify-content: center; margin: 40px 0; }
.loading-wrap { margin-bottom: 30px; }
</style>