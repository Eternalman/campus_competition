import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// 1. 新增：导入中文语言包
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

// 导入时间格式化工具
import { formatTime } from './utils/format'

const app = createApp(App)

// 注册所有图标（保留你原有的逻辑，完全不变）
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 2. 修改：注册Element Plus时，配置中文语言
app.use(ElementPlus, {
  locale: zhCn,
})
// ✅ 全局注册时间格式化过滤器
app.config.globalProperties.$formatTime = formatTime

app.use(router)
app.mount('#app')