import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// 创建一个 Axios 实例
const apiClient = axios.create({
  // 重要：这里的基础 URL 应该指向你的 FastAPI 后端地址
  // 在开发环境下，Vite dev server 和 FastAPI 后端可能不在同一个端口
  baseURL: 'http://127.0.0.1:8000', // 请确保这个地址和端口与你后端运行的一致
  headers: {
    'Content-Type': 'application/json'
  }
})

// 添加请求拦截器
apiClient.interceptors.request.use(config => {
  // 从 localStorage 获取 token
  const token = localStorage.getItem('access_token');
  
  // 如果 token 存在，则在每个请求的 header 中附加 token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
}, error => {
  // 对请求错误做些什么
  return Promise.reject(error);
});

// 添加响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    // 对响应数据做点什么
    return response
  },
  async (error) => {
    const originalRequest = error.config
    const authStore = useAuthStore()

    // 检查是否是401错误，并且不是刷新token的请求本身
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true // 标记为已重试

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        // 调用刷新token的API
        const response = await axios.post('http://127.0.0.1:8000/auth/refresh', 
          `refresh_token=${refreshToken}`,
          {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded'
            }
          }
        )

        const { access_token } = response.data

        // 更新 Pinia store 和 localStorage
        authStore.setToken(access_token, refreshToken)

        // 更新原始请求的 Authorization header
        originalRequest.headers['Authorization'] = `Bearer ${access_token}`

        // 重新发送原始请求
        return apiClient(originalRequest)
      } catch (refreshError) {
        console.error('Unable to refresh token:', refreshError)
        // 如果刷新token失败，则登出用户
        authStore.logout()
        router.push('/login')
        return Promise.reject(refreshError)
      }
    }

    // 对响应错误做点什么
    return Promise.reject(error)
  }
)

export default apiClient