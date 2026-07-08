<template>
  <div class="home-page">
    <!-- 筛选区域 -->
    <div class="filter-wrapper">
      <!-- 分类筛选：单独写「全部」按钮，接口数据容错处理 -->
      <div class="filter-item">
        <span class="filter-label">分类：</span>
        <el-button 
          :type="searchForm.category === null ? 'primary' : 'default'" 
          @click="handleCategoryChange(null)"
        >
          全部
        </el-button>
        <el-button
          v-for="item in categoryOptions"
          :key="item.id"
          :type="searchForm.category === item.id ? 'primary' : 'default'"
          @click="handleCategoryChange(item.id)"
        >
          {{ item.name }}
        </el-button>
      </div>

      <!-- 等级筛选：完整的等级选项 -->
      <div class="filter-item">
        <span class="filter-label">等级：</span>
        <el-button 
          :type="searchForm.level === null ? 'primary' : 'default'" 
          @click="handleLevelChange(null)"
        >
          全部
        </el-button>
        <el-button
          :type="searchForm.level === 'school' ? 'primary' : 'default'"
          @click="handleLevelChange('school')"
        >
          校级
        </el-button>
        <el-button
          :type="searchForm.level === 'city' ? 'primary' : 'default'"
          @click="handleLevelChange('city')"
        >
          市级
        </el-button>
        <el-button
          :type="searchForm.level === 'province' ? 'primary' : 'default'"
          @click="handleLevelChange('province')"
        >
          省级
        </el-button>
        <el-button
          :type="searchForm.level === 'national' ? 'primary' : 'default'"
          @click="handleLevelChange('national')"
        >
          国家级
        </el-button>
      </div>

      <!-- 排序切换 -->
      <div class="sort-wrapper">
        <el-button :type="currentTab === 'latest' ? 'primary' : 'default'" @click="handleTabChange('latest')">最新</el-button>
        <el-button :type="currentTab === 'hottest' ? 'primary' : 'default'" @click="handleTabChange('hottest')">最热</el-button>
      </div>
    </div>

    <!-- 加载提示 -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 赛事列表 -->
    <div v-else class="competition-list">
      <template v-if="competitionList.length > 0">
        <div 
          v-for="competition in competitionList" 
          :key="competition.id" 
          class="competition-card"
          @click="goDetail(competition)"
        >
          <!-- 【保留】你原来的封面路径处理逻辑，完美兼容后端相对路径 -->
          <div class="card-cover">
            <img 
              :src="competition.cover || getPlaceholderImage(competition.id)" 
              :alt="competition.title"
              @error="e => e.target.src=getPlaceholderImage(competition.id)"
            />
          </div>
          <div class="card-info">
            <h3 class="card-title">{{ competition.title || '未知赛事' }}</h3>
            <div class="card-meta">
              <el-tag v-if="competition.level === 'school'" size="small">{{ getLevelText(competition.level) }}</el-tag>
              <el-tag v-else-if="competition.level === 'city'" size="small" type="success">{{ getLevelText(competition.level) }}</el-tag>
              <el-tag v-else-if="competition.level === 'province'" size="small" type="warning">{{ getLevelText(competition.level) }}</el-tag>
              <el-tag v-else size="small" type="danger">{{ getLevelText(competition.level) }}</el-tag>
              <span class="organizer">{{ competition.organizer || '未知组织方' }}</span>
              <span class="view-count">{{ competition.view_count || 0 }}次浏览</span>
            </div>
          </div>
        </div>
      </template>
      
      <!-- 空数据提示 -->
      <el-empty v-else description="暂无符合条件的赛事" class="empty-wrap" />
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[12, 16, 24, 32]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()

// ========== 核心变量定义 ==========
const loading = ref(false)
const currentTab = ref('latest')
const competitionList = ref([])
const categoryOptions = ref([])

// 搜索筛选表单
const searchForm = ref({
  category: null,
  level: null
})

// 分页
const pagination = ref({
  page: 1,
  size: 12,
  total: 0
})

// ========== 工具函数 ==========
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

// 跳转到赛事详情页
const goDetail = (item) => {
  if (!item?.id) return
  router.push(`/competition/${item.id}`)
}

// 生成唯一的占位图URL，避免重复
const getPlaceholderImage = (id) => {
  return `https://picsum.photos/400/220?random=${id || Date.now()}`
}

// 处理分类筛选改变
const handleCategoryChange = (categoryId) => {
  searchForm.value.category = categoryId
  pagination.value.page = 1
  getCompetitionList()
}

// 处理等级筛选改变
const handleLevelChange = (level) => {
  searchForm.value.level = level
  pagination.value.page = 1
  getCompetitionList()
}

// 处理排序切换
const handleTabChange = (tab) => {
  currentTab.value = tab
  pagination.value.page = 1
  getCompetitionList()
}

// 处理每页显示数量改变
const handleSizeChange = (size) => {
  pagination.value.size = size
  pagination.value.page = 1
  getCompetitionList()
}

// 处理页码改变
const handlePageChange = (page) => {
  pagination.value.page = page
  getCompetitionList()
  // 滚动到页面顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ========== 接口请求 ==========
// 【优化】获取分类选项：完美兼容DRF分页和直接数组两种返回格式
const getCategoryOptions = async () => {
  try {
    const res = await request.get('/category-options/')
    // 兼容两种返回格式：分页包裹 / 直接数组
    categoryOptions.value = Array.isArray(res.results) ? res.results : Array.isArray(res) ? res : []
    console.log('分类选项加载成功：', categoryOptions.value)
  } catch (err) {
    categoryOptions.value = []
    console.error('获取分类失败', err)
  }
}

// 【优化】获取赛事列表：只传有值的参数，避免空值干扰后端
const getCompetitionList = async () => {
  loading.value = true
  try {
    // 只传有值的参数，避免后端不识别空参数
    const params = {}
    if (pagination.value.page) params.page = pagination.value.page
    if (pagination.value.size) params.page_size = pagination.value.size
    if (searchForm.value.category) params.category = searchForm.value.category
    if (searchForm.value.level) params.level = searchForm.value.level
    if (route.query.keyword) params.search = route.query.keyword

    // 排序逻辑：最新按创建时间，最热按浏览量（后端已支持）
    if (currentTab.value === 'hottest') {
      params.sort = 'hot'
    }

    console.log('赛事列表请求参数：', params)
    const res = await request.get('/competitions/', { params })
    console.log('赛事列表接口返回：', res)

    // 兼容两种返回结构：分页包裹 / 直接数组
    if (Array.isArray(res)) {
      competitionList.value = res
      pagination.value.total = res.length
    } else {
      competitionList.value = Array.isArray(res.results) ? res.results : []
      pagination.value.total = res.count || res.results?.length || 0
    }
  } catch (err) {
    competitionList.value = []
    pagination.value.total = 0
    ElMessage.error('获取赛事列表失败')
    console.error('获取赛事列表报错：', err)
  } finally { 
    loading.value = false
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  getCategoryOptions()
  getCompetitionList()
})

// 监听路由参数变化（比如顶部搜索）重新请求
watch(() => route.query.keyword, () => {
  pagination.value.page = 1
  getCompetitionList()
})
</script>

<style scoped>
.home-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.filter-wrapper {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.filter-item {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
}

.filter-item:last-child {
  margin-bottom: 0;
}

.filter-label {
  font-size: 14px;
  color: #606266;
  width: 50px;
}

.sort-wrapper {
  display: flex;
  gap: 12px;
}

.loading-wrap {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.empty-wrap {
  margin: 40px auto;
}

.competition-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.competition-card {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.competition-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.card-cover {
  width: 100%;
  height: 180px;
  overflow: hidden;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.competition-card:hover .card-cover img {
  transform: scale(1.05);
}

.card-info {
  padding: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.organizer {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.view-count {
  color: #f56c6c;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 30px 0;
}

.pagination-wrapper :deep(.el-pagination) {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.pagination-wrapper :deep(.el-pager li) {
  border-radius: 6px;
  margin: 0 4px;
  font-weight: 500;
}

.pagination-wrapper :deep(.el-pager li.is-active) {
  background-color: #409eff;
  color: #fff;
}

.pagination-wrapper :deep(.btn-prev),
.pagination-wrapper :deep(.btn-next) {
  border-radius: 6px;
}

.pagination-wrapper :deep(.el-select .el-input__wrapper) {
  border-radius: 6px;
}

/* 响应式适配 */
@media (max-width: 1200px) {
  .competition-list {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .competition-list {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>