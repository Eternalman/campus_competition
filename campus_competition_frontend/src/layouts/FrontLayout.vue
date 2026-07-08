<template>
  <div class="front-layout">
    <!-- 前台导航栏 -->
    <Header />
    <!-- 页面内容区域（留60px顶部间距） -->
    <main class="page-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
// 导入前台导航栏组件
import Header from '@/components/Header.vue'
</script>

<style scoped>
.front-layout {
  width: 100%;
  min-height: 100vh;
  background-color: #f5f7fa;
}
.page-content {
  padding-top: 60px; /* 给Header留高度 */
  max-width: 1400px;
  margin: 0 auto;
  padding-left: 20px;
  padding-right: 20px;
  padding-bottom: 40px;
}
</style>