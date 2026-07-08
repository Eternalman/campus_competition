import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout: 10000
})

// 请求拦截器：自动携带token（前后台分离）
request.interceptors.request.use(
  config => {
    // const token = localStorage.getItem('token')
    const currentPath = router.currentRoute.value.path
    let token
    if (currentPath.startsWith('/admin')) {
      token = localStorage.getItem('admin_token')
    } else {
      token = localStorage.getItem('front_token')
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  err => {
    return Promise.reject(err)
  }
)

// 响应拦截器：统一处理错误
request.interceptors.response.use(
  response => response.data, // 直接返回 data，简化页面代码
  error => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          // localStorage.removeItem('token')
          // localStorage.removeItem('userInfo')
          localStorage.removeItem('admin_token')
          localStorage.removeItem('admin_refreshToken')
          localStorage.removeItem('admin_userInfo')
          // 区分前台/后台跳转
          const currentPath = router.currentRoute.value.path
          if (currentPath.startsWith('/admin')) {
            router.push('/admin/login')
          } else {
            localStorage.removeItem('front_token')
            localStorage.removeItem('front_refreshToken')
            localStorage.removeItem('front_userInfo')
            router.push('/login')
          }
          break
        case 403:
          ElMessage.error('没有权限访问该资源')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误，请稍后重试')
          break
        default:
          ElMessage.error(error.response.data?.detail || error.response.data?.msg || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default request