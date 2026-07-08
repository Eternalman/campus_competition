<template>
  <div class="score-management">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>评分管理</span>
        </div>
      </template>

      <!-- 筛选区域 -->
      <el-form :inline="true" :model="queryForm" class="demo-form-inline">
        <el-form-item label="赛事">
          <el-select v-model="queryForm.competition" placeholder="请选择赛事" clearable style="width: 200px" @change="fetchData">
            <el-option
              v-for="item in competitions"
              :key="item.id"
              :label="item.title"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="tableData" style="width: 100%" border>
        <el-table-column prop="competition_title" label="赛事名称" width="200" />
        <el-table-column prop="user_name" label="参赛人" width="150" />
        <el-table-column label="评委评分">
          <template #default="scope">
            <div v-for="(scoreInfo, judgeId) in scope.row.judge_scores" :key="judgeId" class="judge-score-item">
              <span style="font-weight: bold">{{ scoreInfo.nickname }}:</span>
              <el-input
                v-model="scoreInfo.tempScore"
                :disabled="isDisabled(judgeId, scoreInfo)"
                placeholder="请输入分数"
                style="width: 100px; margin-left: 8px"
                type="number"
                :min="0"
                :max="100"
                :precision="2"
              />
              <el-button
                v-if="canEdit(judgeId, scoreInfo)"
                type="primary"
                size="small"
                @click="submitScore(scope.row, judgeId, scoreInfo)"
                :loading="scoreInfo.submitting"
              >
                确定
              </el-button>
              <el-button
                v-if="canLock(judgeId, scoreInfo)"
                type="success"
                size="small"
                @click="lockScore(scoreInfo)"
                :disabled="scoreInfo.is_locked"
              >
                {{ scoreInfo.is_locked ? '已锁定' : '锁定' }}
              </el-button>
              <el-tag v-if="scoreInfo.is_locked" type="success" size="small" style="margin-left: 8px">已锁定</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="final_score" label="最终评分" width="120">
          <template #default="scope">
            <span v-if="scope.row.final_score !== null" style="font-weight: bold; color: #409eff">
              {{ scope.row.final_score.toFixed(2) }}
            </span>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 'finished'" type="success">已完成</el-tag>
            <el-tag v-else type="info">进行中</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchData"
        @current-change="fetchData"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

// 获取当前登录用户信息
const currentUser = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('admin_userInfo') || '{}')
  } catch {
    return {}
  }
})

const queryForm = reactive({
  competition: null,
})

const competitions = ref([])
const tableData = ref([])
const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0,
})

// 判断是否可以编辑某个评委的评分
const canEdit = (judgeId, scoreInfo) => {
  // 管理员可以编辑所有评分，或者是评委自己的评分且未锁定
  if (currentUser.value.role === 'admin') {
    return true
  }
  return currentUser.value.id === parseInt(judgeId) && !scoreInfo.is_locked
}

// 判断输入框是否应该禁用
const isDisabled = (judgeId, scoreInfo) => {
  // 如果已锁定，禁用输入框
  if (scoreInfo.is_locked) {
    return true
  }
  // 管理员可以编辑所有
  if (currentUser.value.role === 'admin') {
    return false
  }
  // 评委只能编辑自己的
  return currentUser.value.id !== parseInt(judgeId)
}

// 判断是否可以锁定
const canLock = (judgeId, scoreInfo) => {
  // 只有评分存在（有分数）时才能锁定
  if (!scoreInfo.id) {
    return false
  }
  // 管理员或者是评分的评委可以锁定
  return currentUser.value.role === 'admin' || currentUser.value.id === parseInt(judgeId)
}

const fetchCompetitions = async () => {
  try {
    const res = await request.get('/competitions/')
    competitions.value = res.results || res
  } catch (err) {
    console.error('获取赛事列表失败', err)
  }
}

const fetchData = async () => {
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (queryForm.competition) {
      params.competition = queryForm.competition
    }
    const res = await request.get('/scores/list-for-management/', { params })
    const data = res.results || res
    
    // 初始化临时分数和提交状态
    data.forEach(row => {
      Object.keys(row.judge_scores).forEach(judgeId => {
        const scoreInfo = row.judge_scores[judgeId]
        scoreInfo.tempScore = scoreInfo.score !== null ? String(scoreInfo.score) : ''
        scoreInfo.submitting = false
      })
    })
    
    tableData.value = data
    pagination.total = res.count || 0
  } catch (err) {
    console.error('获取评分列表失败', err)
    ElMessage.error('获取评分列表失败')
  }
}

const submitScore = async (row, judgeId, scoreInfo) => {
  // 验证分数
  const score = parseFloat(scoreInfo.tempScore)
  if (isNaN(score) || score < 0 || score > 100) {
    ElMessage.warning('请输入0-100之间的分数')
    return
  }

  // 确保judgeId是整数
  const judgeIdInt = parseInt(judgeId)

  scoreInfo.submitting = true
  try {
    if (scoreInfo.id) {
      // 更新现有评分
      await request.put(`/scores/${scoreInfo.id}/`, {
        registration: row.id,
        judge: judgeIdInt,
        score: score,
      })
      ElMessage.success('更新评分成功')
    } else {
      // 添加新评分
      await request.post('/scores/', {
        registration: row.id,
        judge: judgeIdInt,
        score: score,
      })
      ElMessage.success('评分成功')
    }
    fetchData()
  } catch (err) {
    console.error('评分失败', err)
    ElMessage.error(err.response?.data?.detail || '评分失败')
  } finally {
    scoreInfo.submitting = false
  }
}

const lockScore = async (scoreInfo) => {
  if (!scoreInfo.id) {
    ElMessage.warning('请先评分再锁定')
    return
  }
  
  try {
    await request.post(`/scores/${scoreInfo.id}/lock/`)
    ElMessage.success('评分锁定成功')
    fetchData()
  } catch (err) {
    console.error('锁定失败', err)
    ElMessage.error(err.response?.data?.msg || '锁定失败')
  }
}

onMounted(() => {
  fetchCompetitions()
  fetchData()
})
</script>

<style scoped>
.score-management {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.judge-score-item {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.judge-score-item:last-child {
  margin-bottom: 0;
}
</style>
