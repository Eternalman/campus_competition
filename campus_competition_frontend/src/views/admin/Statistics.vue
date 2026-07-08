<template>
  <div class="statistics-page">
    <el-loading v-loading="loading" text="加载中...">
      <div class="chart-row">
        <!-- 上部分：近一周访问量（折线图） -->
        <div class="chart-card full-width">
          <h3 class="chart-title">近一周访问量</h3>
          <div ref="visitChartRef" class="chart-container"></div>
        </div>
      </div>

      <div class="chart-row">
        <!-- 左下：热门赛事排行（柱状图） -->
        <div class="chart-card half-width">
          <h3 class="chart-title">热门赛事排行</h3>
          <div ref="competitionChartRef" class="chart-container"></div>
        </div>

        <!-- 右下：热门分类比例（环形图） -->
        <div class="chart-card half-width">
          <h3 class="chart-title">热门分类比例</h3>
          <div ref="categoryChartRef" class="chart-container"></div>
        </div>
      </div>
    </el-loading>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import request from '@/utils/request'

const visitChartRef = ref(null)
const competitionChartRef = ref(null)
const categoryChartRef = ref(null)

const loading = ref(false)

let visitChart = null
let competitionChart = null
let categoryChart = null

// 初始化折线图（近一周访问量）
const initVisitChart = (data) => {
  if (!visitChartRef.value) return
  visitChart = echarts.init(visitChartRef.value)
  
  const counts = data.map(item => item.count)
  const totalCount = counts.reduce((a, b) => a + b, 0)
  const avgCount = Math.round(totalCount / data.length)
  const maxCount = Math.max(...counts)
  const minCount = Math.min(...counts)
  
  const option = {
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#409eff',
      textStyle: { color: '#303133' },
      formatter: (params) => {
        const date = params[0].axisValue
        const count = params[0].data
        return `${date}<br/>访问量: <span style="color: #409eff; font-weight: bold">${count}</span>`
      }
    },
    title: {
      text: `总计: ${totalCount} 次 | 平均: ${avgCount} 次 | 最高: ${maxCount} 次 | 最低: ${minCount} 次`,
      left: 'center',
      textStyle: {
        fontSize: 14,
        color: '#909399'
      },
      top: 10
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '60px', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map(item => item.date),
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#909399' }
    },
    yAxis: { 
      type: 'value',
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#909399' },
      splitLine: { lineStyle: { color: '#ebeef5' } }
    },
    series: [
      {
        name: '访问量',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        showSymbol: true,
        label: {
          show: true,
          position: 'top',
          color: '#409eff',
          fontWeight: 'bold'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ])
        },
        lineStyle: { color: '#409eff', width: 3 },
        itemStyle: { 
          color: '#409eff',
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          itemStyle: {
            color: '#67c23a',
            borderColor: '#fff',
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: 'rgba(103, 194, 58, 0.5)'
          }
        },
        markPoint: {
          data: [
            { type: 'max', name: '最大值' },
            { type: 'min', name: '最小值' }
          ],
          itemStyle: {
            color: '#f56c6c'
          }
        },
        markLine: {
          data: [
            { type: 'average', name: '平均值' }
          ],
          lineStyle: {
            color: '#e6a23c',
            type: 'dashed'
          }
        },
        data: counts
      }
    ]
  }
  
  visitChart.setOption(option)
  
  // 添加点击事件
  visitChart.on('click', (params) => {
    console.log('点击数据:', params)
  })
}

// 初始化柱状图（热门赛事排行）
const initCompetitionChart = (data) => {
  if (!competitionChartRef.value) return
  competitionChart = echarts.init(competitionChartRef.value)
  
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { 
      type: 'value',
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#909399' },
      splitLine: { lineStyle: { color: '#ebeef5' } }
    },
    yAxis: {
      type: 'category',
      data: data.map(item => item.title).reverse(),
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisLabel: { color: '#909399' }
    },
    series: [
      {
        name: '浏览次数',
        type: 'bar',
        data: data.map(item => item.view_count).reverse(),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#67c23a' },
            { offset: 1, color: '#85ce61' }
          ]),
          borderRadius: [0, 4, 4, 0]
        },
        barWidth: '50%'
      }
    ]
  }
  
  competitionChart.setOption(option)
}

// 初始化环形图（热门分类比例）
const initCategoryChart = (data) => {
  if (!categoryChartRef.value) return
  categoryChart = echarts.init(categoryChartRef.value)
  
  // 过滤掉值为0的分类
  const filteredData = data.filter(item => item.value > 0)
  
  const option = {
    tooltip: { 
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: { 
      orient: 'vertical', 
      left: 'left',
      top: 'center',
      textStyle: { color: '#606266' }
    },
    series: [
      {
        name: '赛事数量',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { 
          show: true, 
          formatter: '{b}: {c}',
          color: '#606266'
        },
        emphasis: {
          label: { show: true, fontSize: 16, fontWeight: 'bold' },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        data: filteredData
      }
    ]
  }
  
  categoryChart.setOption(option)
}

// 获取数据并渲染图表
const getData = async () => {
  loading.value = true
  try {
    // 并行请求三个接口
    const [visitRes, competitionRes, categoryRes] = await Promise.all([
      request.get('/statistics/visit-trend/'),
      request.get('/statistics/hot-competition/'),
      request.get('/statistics/category-ratio/')
    ])

    initVisitChart(visitRes || [])
    initCompetitionChart(competitionRes || [])
    initCategoryChart(categoryRes || [])
  } catch (error) {
    console.error('获取统计数据失败:', error)
    // 如果接口没通，给点模拟数据展示效果
    initVisitChart([
      { date: '02-17', count: 120 },
      { date: '02-18', count: 200 },
      { date: '02-19', count: 150 },
      { date: '02-20', count: 280 },
      { date: '02-21', count: 230 },
      { date: '02-22', count: 310 },
      { date: '02-23', count: 450 }
    ])
    initCompetitionChart([
      { title: '大学生英语竞赛', view_count: 720 },
      { title: '大学生物理竞赛', view_count: 342 },
      { title: '全国研究生演讲大赛', view_count: 143 },
      { title: '大学生设计竞赛', view_count: 65 },
      { title: '无人机组装大赛', view_count: 55 }
    ])
    initCategoryChart([
      { name: '学术类', value: 5 },
      { name: '文艺类', value: 2 },
      { name: '科技类', value: 4 },
      { name: '体育类', value: 1 }
    ])
  } finally {
    loading.value = false
  }
}

// 窗口大小改变时重绘图表
const handleResize = () => {
  visitChart && visitChart.resize()
  competitionChart && competitionChart.resize()
  categoryChart && categoryChart.resize()
}

onMounted(() => {
  getData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  // 销毁图表实例，防止内存泄漏
  visitChart && visitChart.dispose()
  competitionChart && competitionChart.dispose()
  categoryChart && categoryChart.dispose()
})
</script>

<style scoped>
.statistics-page {
  background: #f5f7fa;
  min-height: calc(100vh - 140px);
  padding: 0;
}
.chart-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.full-width {
  width: 100%;
}
.half-width {
  width: 50%;
}
.chart-title {
  font-size: 18px;
  color: #303133;
  margin: 0 0 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}
.chart-container {
  width: 100%;
  height: 350px;
}
</style>