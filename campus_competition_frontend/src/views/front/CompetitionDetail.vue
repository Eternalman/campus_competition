<template>
  <div class="detail-page">
    <!-- 加载提示 -->
    <div class="loading-wrap" v-if="loading">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 赛事详情内容 -->
    <div class="detail-content" v-else>
      <div class="detail-card" v-if="competitionInfo">
        <!-- 头部信息 -->
        <div class="detail-header">
          <div class="cover-img">
            <img 
              :src="competitionInfo.cover || getPlaceholderImage(competitionInfo.id)"
              :alt="competitionInfo.title"
              @error="e => e.target.src=getPlaceholderImage(competitionInfo.id)"
            />
          </div>
          <div class="header-info">
            <div class="title-row">
              <el-tag type="success" v-if="competitionInfo.status === 'published'">有效</el-tag>
              <el-tag type="info" v-else-if="competitionInfo.status === 'draft'">草稿</el-tag>
              <el-tag type="danger" v-else>已结束</el-tag>
              <h1 class="title">{{ competitionInfo.title }}</h1>
            </div>
            <div class="view-row">
              <span class="view-count">{{ competitionInfo.view_count || 0 }}次浏览</span>
            </div>
            <div class="info-list">
              <div class="info-item">
                <span class="label">分类：</span>
                <span class="value">{{ competitionInfo.category_name || '未知分类' }}</span>
              </div>
              <div class="info-item">
                <span class="label">等级：</span>
                <span class="value">{{ getLevelText(competitionInfo.level) }}</span>
              </div>
              <div class="info-item">
                <span class="label">组织方：</span>
                <span class="value">{{ competitionInfo.organizer }}</span>
              </div>
              <div class="info-item">
                <span class="label">报名时间：</span>
                <span class="value">{{ $formatTime(competitionInfo.registration_time) }}</span>
              </div>
              <div class="info-item">
                <span class="label">竞赛时间：</span>
                <span class="value">{{ $formatTime(competitionInfo.competition_time) }}</span>
              </div>
              <div class="info-item">
                <span class="label">竞赛地点：</span>
                <span class="value">{{ competitionInfo.location }}</span>
              </div>
            </div>
            <div class="action-row">
              <el-button type="primary" size="large" @click="goRegister" :disabled="isRegistered || competitionInfo.status !== 'published'">
                {{ isRegistered ? '已报名' : competitionInfo.status !== 'published' ? '报名已结束' : '+ 立即报名' }}
              </el-button>
              <el-button @click="handleLike">{{ likeCount }} 点赞</el-button>
              <el-button @click="handleCollect">{{ collectCount }} 收藏</el-button>
              <el-button @click="handleShare">分享</el-button>
            </div>
          </div>
        </div>

        <!-- 赛事简介 -->
        <div class="intro-box">
          <h3 class="intro-title">赛事简介</h3>
          <div class="intro-content">
            {{ competitionInfo.description || '暂无赛事简介' }}
          </div>
        </div>
      </div>

      <!-- 相关推荐 -->
      <div class="recommend-box">
        <h3 class="recommend-title">相关推荐</h3>
        <div class="recommend-list">
          <div v-for="item in recommendList" :key="item.id" class="recommend-item" @click="goDetail(item)">
            <img 
              :src="item.cover || getRecommendPlaceholderImage(item.id)" 
              :alt="item.title"
              @error="e => e.target.src=getRecommendPlaceholderImage(item.id)"
            />
            <div class="item-info">
              <h4>{{ item.title }}</h4>
              <p>{{ getLevelText(item.level) }} {{ item.organizer }} {{ item.view_count || 0 }}次浏览</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空数据提示 -->
    <el-empty v-if="!loading && !competitionInfo" description="赛事不存在或已被删除" />
  </div>
</template>

<script setup>
import { ref, onMounted,onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()
const competitionId = route.params.id // 从路由获取赛事ID

// 基础数据
const loading = ref(false)
const competitionInfo = ref({})
const recommendList = ref([])
const likeCount = ref(6)
const collectCount = ref(6)
const isRegistered = ref(false)
// 浏览计时相关
const enterTime = ref(0) // 进入页面的时间戳
const hasViewed = ref(false) // 是否已统计过本次浏览


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

// 获取赛事详情
const getCompetitionDetail = async () => {
  if (!competitionId) {
    ElMessage.error('赛事ID不存在')
    router.push('/')
    return
  }

  loading.value = true
  try {
    console.log('正在获取赛事详情，ID：', competitionId)
    const res = await request.get(`/competitions/${competitionId}/`)
    console.log('赛事详情接口返回：', res)
    competitionInfo.value = res

    // ✅ 修复2：记录进入页面的时间（之前漏掉了，导致浏览量统计失效）
    enterTime.value = Date.now()

    // 检查当前用户是否已报名
    checkIsRegistered()
    // 获取相关推荐
    getRecommendList()
  } catch (err) {
    ElMessage.error('获取赛事详情失败，赛事可能不存在')
    console.error('赛事详情报错：', err)
    competitionInfo.value = null
  } finally {
    loading.value = false
  }
}

// 检查当前用户是否已报名
const checkIsRegistered = async () => {
  const token = localStorage.getItem('front_token')
  if (!token) return
  try {
    const res = await request.get('/registrations/my/')
    isRegistered.value = res.some(item => item.competition === Number(competitionId))
  } catch (err) {
    console.error('检查报名状态失败', err)
  }
}

// 获取相关推荐
const getRecommendList = async () => {
  try {
    const res = await request.get('/competitions/', {
      params: { page_size: 4, category: competitionInfo.value.category }
    })
    recommendList.value = res.results || res || []
    // 过滤掉当前赛事
    recommendList.value = recommendList.value.filter(item => item.id !== Number(competitionId))
  } catch (err) {
    console.error('获取推荐列表失败', err)
  }
}

// 跳转到报名页
const goRegister = () => {
  const token = localStorage.getItem('front_token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  if (isRegistered.value) {
    ElMessage.info('您已经报名过该赛事了')
    return
  }
  if (competitionInfo.value.status !== 'published') {
    ElMessage.warning('该赛事暂未开放报名')
    return
  }
  router.push(`/competition/${competitionId}/register`)
}

// 跳转详情
const goDetail = (item) => {
  router.push(`/competition/${item.id}`)
  // ✅ 修复3：去掉不必要的刷新，Vue路由会自动重新加载组件
  // window.location.reload()
}

// 生成唯一的占位图URL，避免重复
const getPlaceholderImage = (id) => {
  return `https://picsum.photos/400/300?random=${id || Date.now()}`
}

// 生成推荐列表的唯一占位图URL
const getRecommendPlaceholderImage = (id) => {
  return `https://picsum.photos/200/120?random=${id || Date.now()}`
}

// 模拟功能
const handleLike = () => { likeCount.value++; ElMessage.success('点赞成功') }
const handleCollect = () => { collectCount.value++; ElMessage.success('收藏成功') }
const handleShare = () => { ElMessage.success('分享链接已复制') }


// ========== 浏览统计逻辑（简化版，避免影响浏览器行为） ==========
const hasCounted = ref(false)

const countView = async () => {
  if (hasCounted.value) return
  
  const stayTime = Date.now() - enterTime.value
  console.log('页面停留时间：', stayTime, 'ms')

  // 只判断：停留超过1秒
  if (stayTime > 1000) {
    console.log('满足条件，发送浏览量统计请求')
    try {
      await request.post(`/competitions/${competitionId}/add-view/`)
      console.log('✅ 浏览量统计成功')
      hasCounted.value = true
    } catch (err) {
      console.error('❌ 浏览量统计失败：', err)
    }
  } else {
    console.log('⏱️ 停留时间不足1秒，跳过统计')
  }
}

// 页面可见性变化时也统计（更可靠）
const handleVisibilityChange = () => {
  if (document.visibilityState === 'hidden') {
    countView()
  }
}

// 监听场景：路由离开 + 页面隐藏
onMounted(() => {
  getCompetitionDetail()
  // 记录进入页面的时间
  enterTime.value = Date.now()
  // 使用 visibilitychange 替代 beforeunload，避免影响浏览器行为
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  // 路由跳转离开时统计
  countView()
  // 移除事件监听
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.detail-page { min-height: 100vh; background-color: #f5f7fa; }
.logo { font-size: 20px; font-weight: bold; color: #409eff; cursor: pointer; }
.nav { display: flex; gap: 32px; }
.nav-item { font-size: 16px; color: #606266; transition: all 0.3s; text-decoration: none; padding-bottom: 4px; border-bottom: 2px solid transparent; }
.nav-item:hover, .nav-item.active { color: #409eff; border-bottom-color: #409eff; }

.loading-wrap { max-width: 1400px; margin: 30px auto; padding: 0 20px; }
.detail-content { max-width: 1400px; margin: 0 auto; padding: 30px 20px; display: grid; grid-template-columns: 1fr 280px; gap: 24px; }
.detail-card { background: #fff; border-radius: 12px; overflow: hidden; padding: 24px; }
.detail-header { display: grid; grid-template-columns: 300px 1fr; gap: 24px; margin-bottom: 24px; }
.cover-img { width: 100%; height: 220px; border-radius: 8px; overflow: hidden; }
.cover-img img { width: 100%; height: 100%; object-fit: cover; }
.title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.title { font-size: 28px; font-weight: 700; color: #303133; margin: 0; }
.view-row { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.view-count { font-size: 14px; color: #909399; }
.info-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 24px; }
.info-item { font-size: 15px; }
.info-item .label { color: #909399; }
.info-item .value { color: #303133; font-weight: 500; }
.action-row { display: flex; gap: 12px; flex-wrap: wrap; }

.intro-box { border-top: 1px solid #f0f0f0; padding-top: 20px; }
.intro-title { font-size: 18px; font-weight: 600; color: #303133; margin: 0 0 16px 0; }
.intro-content { font-size: 15px; line-height: 1.8; color: #606266; white-space: pre-line; }

.recommend-box { background: #fff; border-radius: 12px; padding: 20px; height: fit-content; }
.recommend-title { font-size: 18px; font-weight: 600; margin: 0 0 16px 0; color: #303133; }
.recommend-list { display: flex; flex-direction: column; gap: 16px; }
.recommend-item { display: flex; gap: 12px; cursor: pointer; transition: all 0.3s; }
.recommend-item:hover { opacity: 0.8; }
.recommend-item img { width: 100px; height: 60px; border-radius: 6px; object-fit: cover; flex-shrink: 0; }
.item-info h4 { font-size: 14px; font-weight: 500; margin: 0 0 6px 0; color: #303133; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.item-info p { font-size: 12px; color: #909399; margin: 0; }
</style>