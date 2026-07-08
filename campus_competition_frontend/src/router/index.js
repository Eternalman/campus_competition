import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

// ========== 新增：导入布局组件 ==========
import FrontLayout from '@/layouts/FrontLayout.vue' // 前台布局
import AdminLayout from '@/views/admin/Layout.vue'   // 后台布局

// ========== 页面组件导入 ==========
// 前台页面
const Home = () => import('@/views/front/Home.vue')
const Hot = () => import('@/views/front/Hot.vue')
const Profile = () => import('@/views/front/Profile.vue')
const FrontLogin = () => import('@/views/front/Login.vue')
const AIAssistantPage = () => import('@/views/front/AIAssistant.vue')
const FrontRegister = () => import('@/views/front/Register.vue')
// 赛事相关页面
const CompetitionDetail = () => import('@/views/front/CompetitionDetail.vue')
const CompetitionRegister = () => import('@/views/front/CompetitionRegister.vue')
const RegisterSuccess = () => import('@/views/front/RegisterSuccess.vue')
const MyRegistrations = () => import('@/views/front/MyRegistrations.vue')
// 后台页面
const AdminLogin = () => import('@/views/admin/Login.vue')
const Competition = () => import('@/views/admin/Competition.vue')
const Category = () => import('@/views/admin/Category.vue')
const User = () => import('@/views/admin/User.vue')
const Registration = () => import('@/views/admin/Registration.vue')
const Notice = () => import('@/views/admin/Notice.vue')
const LoginLog = () => import('@/views/admin/Logs/LoginLog.vue')
const OperationLog = () => import('@/views/admin/Logs/OperationLog.vue')
const ErrorLog = () => import('@/views/admin/Logs/ErrorLog.vue')
const Statistics = () => import('@/views/admin/Statistics.vue')
const Message = () => import('@/views/admin/Message.vue')
const SystemInfo = () => import('@/views/admin/SystemInfo.vue')
const ScoreManagement = () => import('@/views/admin/ScoreManagement.vue')
const KnowledgeBase = () => import('@/views/admin/KnowledgeBase.vue')

// ========== 路由表 ==========
const routes = [
  // ========== 前台路由（绑定FrontLayout布局） ==========
  {
    path: '/',
    component: FrontLayout, // 前台布局（包含Header）
    children: [
      { path: '', name: 'Home', component: Home },
      { path: 'hot', name: 'Hot', component: Hot },
      { path: 'ai-assistant', name: 'AIAssistant', component: AIAssistantPage },
      // 赛事详情页
      { path: 'competition/:id', name: 'CompetitionDetail', component: CompetitionDetail },
      // 赛事报名页（需要登录）
      { 
        path: 'competition/:id/register', 
        name: 'CompetitionRegister', 
        component: CompetitionRegister, 
        meta: { requiresAuth: true } 
      },
      // 报名成功页（需要登录）
      { path: 'register/success', name: 'RegisterSuccess', component: RegisterSuccess, meta: { requiresAuth: true } },
      // 个人中心（需要登录）
      { 
        path: 'profile', 
        name: 'Profile', 
        component: Profile,
        meta: { requiresAuth: true },
        redirect: '/profile/registrations',
        children: [
          { path: 'registrations', name: 'MyRegistrations', component: MyRegistrations }
        ]
      }
    ]
  },
  // 前台登录/注册页（不绑定布局，单独显示）
  { path: '/login', name: 'FrontLogin', component: FrontLogin },
  { path: '/register', name: 'FrontRegister', component: FrontRegister },

  // ========== 后台路由 ==========
  { path: '/admin/login', name: 'AdminLogin', component: AdminLogin },
  {
    path: '/admin',
    component: AdminLayout,
    redirect: '/admin/competition',
    children: [
      { path: 'competition', name: 'Competition', component: Competition },
      { path: 'category', name: 'Category', component: Category },
      { path: 'user', name: 'User', component: User },
      { path: 'registration', name: 'Registration', component: Registration },
      { path: 'notice', name: 'Notice', component: Notice },
      { path: 'login-log', name: 'LoginLog', component: LoginLog },
      { path: 'operation-log', name: 'OperationLog', component: OperationLog },
      { path: 'error-log', name: 'ErrorLog', component: ErrorLog },
      { path: 'statistics', name: 'Statistics', component: Statistics },
      { path: 'message', name: 'Message', component: Message },
      { path: 'system-info', name: 'SystemInfo', component: SystemInfo },
      { path: 'score-management', name: 'ScoreManagement', component: ScoreManagement },
      { path: 'knowledge-base', name: 'KnowledgeBase', component: KnowledgeBase },
    ]
  }
]

// ========== 路由实例 ==========
const router = createRouter({
  history: createWebHistory(),
  routes
})

// ========== 全局前置守卫 ==========
router.beforeEach((to, from, next) => {
  // 1. 访问后台管理页面（非登录页）：校验管理员权限
  if (to.path.startsWith('/admin') && to.path !== '/admin/login') {
    const adminToken = localStorage.getItem('admin_token')
    let adminUserInfo = {}
    try {
      const userInfoStr = localStorage.getItem('admin_userInfo')
      if (userInfoStr && userInfoStr !== 'undefined') {
        adminUserInfo = JSON.parse(userInfoStr)
      }
    } catch (err) {
      console.warn('管理员信息解析失败，已自动重置', err)
      localStorage.removeItem('admin_userInfo')
      adminUserInfo = {}
    }

    if (!adminToken) {
      ElMessage.warning('请先登录后台')
      next('/admin/login')
      return
    }
    if (adminUserInfo.role !== 'admin' && adminUserInfo.role !== 'judge') {
      ElMessage.error('非管理员或评委账号，请使用对应账号登录')
      next('/admin/login')
      return
    }
    next()
    return
  }

  // 2. 访问前台需要登录的页面
  if (to.meta.requiresAuth) {
    const frontToken = localStorage.getItem('front_token')
    if (!frontToken) {
      ElMessage.warning('请先登录')
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
    next()
    return
  }

  // 3. 已登录用户，禁止重复访问前台登录/注册页
  const frontToken = localStorage.getItem('front_token')
  if (frontToken && ['/login', '/register'].includes(to.path)) {
    ElMessage.info('您已登录')
    next('/')
    return
  }

  next()
})

export default router