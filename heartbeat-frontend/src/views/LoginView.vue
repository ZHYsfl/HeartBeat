<template> 
  <div class="login-container"> 
    <div class="login-form"> 
      <h1 class="title">HeartBeat</h1> 
      <p class="subtitle">心有灵犀</p> 

      <div class="input-group"> 
        <input type="text" v-model="username" placeholder="你的名字" @keyup.enter="handleLogin"> 
      </div> 

      <div class="input-group"> 
        <input type="password" v-model="password" placeholder="约定" @keyup.enter="handleLogin"> 
      </div> 
      
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p> 

      <button @click="handleLogin" class="login-button" :disabled="isLoading"> 
        {{ isLoading ? '连接中...' : '进入我们的世界' }} 
      </button> 
      <div class="register-link"> 
        还没有账户？ <router-link to="/register">立即注册</router-link> 
      </div> 
    </div> 
  </div> 
</template> 

<script setup> 
import { ref } from 'vue' 
import { useRouter } from 'vue-router' 
import apiClient from '@/api' // 导入我们配置好的 apiClient 
import { useAuthStore } from '@/stores/auth'

// --- 响应式状态 --- 
const username = ref('') // 绑定输入框的用户名 
const password = ref('') // 绑定输入框的密码 
const errorMessage = ref('') // 用于显示登录失败的错误信息 
const isLoading = ref(false) // 用于控制按钮的加载状态 

const router = useRouter() // 获取路由实例，用于页面跳转 
const authStore = useAuthStore()

// --- 方法 --- 
const handleLogin = async () => { 
  if (!username.value || !password.value) { 
    errorMessage.value = '名字和约定都不能为空哦' 
    return 
  } 
  
  isLoading.value = true 
  errorMessage.value = '' 

  // FastAPI 的 /auth/token 接口需要 form-data 格式 
  const formData = new URLSearchParams() 
  formData.append('username', username.value) 
  formData.append('password', password.value) 

  try { 
    // 发送登录请求 
    const response = await apiClient.post('/auth/token', formData, { 
      headers: { 
        'Content-Type': 'application/x-www-form-urlencoded' 
      } 
    }) 

    // 登录成功 
    const { access_token, refresh_token } = response.data 
    authStore.setToken(access_token, refresh_token)
    
    // 跳转到主页 
    router.push({ name: 'home' }) 

  } catch (error) { 
    // 处理登录失败 
    if (error.response && error.response.status === 401) { 
      errorMessage.value = '名字或约定不对哦，再试一次吧！' 
    } else { 
      errorMessage.value = '服务器好像开小差了，请稍后再试。' 
      console.error('Login error:', error) 
    } 
  } finally { 
    isLoading.value = false 
  } 
} 
</script> 

<style scoped> 
.login-container { 
  display: flex; 
  justify-content: center; 
  align-items: center; 
  height: 100vh; 
  background-color: #fce4ec; /* 温馨的淡粉色背景 */ 
} 

.login-form { 
  background: white; 
  padding: 40px 30px; 
  border-radius: 16px; 
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1); 
  width: 300px; 
  text-align: center; 
} 

.title { 
  font-size: 28px; 
  color: #e91e63; /* 主题粉色 */ 
  margin-bottom: 5px; 
} 

.subtitle { 
  color: #aaa; 
  margin-bottom: 30px; 
} 

.input-group { 
  margin-bottom: 20px; 
} 

.input-group input { 
  width: 100%; 
  padding: 12px 15px; 
  border-radius: 8px; 
  border: 1px solid #ddd; 
  box-sizing: border-box; /* 确保 padding 不会撑大宽度 */ 
  transition: border-color 0.3s; 
} 

.input-group input:focus { 
  outline: none; 
  border-color: #e91e63; 
} 

.error-message { 
  color: #f44336; /* 红色错误提示 */ 
  font-size: 14px; 
  height: 20px; 
} 

.login-button { 
  width: 100%; 
  padding: 12px; 
  border: none; 
  background-color: #e91e63; 
  color: white; 
  border-radius: 8px; 
  font-size: 16px; 
  cursor: pointer; 
  transition: background-color 0.3s; 
} 

.login-button:hover { 
  background-color: #c2185b; 
} 

.login-button:disabled { 
  background-color: #f8bbd0; 
  cursor: not-allowed; 
} 

.register-link { 
  margin-top: 20px; 
  font-size: 14px; 
} 

.register-link a { 
  color: #e91e63; 
  text-decoration: none; 
  font-weight: bold; 
} 
</style>