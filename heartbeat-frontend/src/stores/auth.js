import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token'))
  const refreshToken = ref(localStorage.getItem('refresh_token'))
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  async function fetchUser() {
    if (token.value) {
      try {
        const response = await apiClient.get('/users/me')
        user.value = response.data
        localStorage.setItem('user', JSON.stringify(response.data))
      } catch (error) {
        console.error('Failed to fetch user:', error)
        clearToken()
      }
    }
  }

  function setToken(tokenValue, refreshTokenValue) {
    token.value = tokenValue
    localStorage.setItem('access_token', tokenValue)
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${tokenValue}`
    if (refreshTokenValue) {
      refreshToken.value = refreshTokenValue
      localStorage.setItem('refresh_token', refreshTokenValue)
    }
    fetchUser()
  }

  function clearToken() {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    delete apiClient.defaults.headers.common['Authorization']
  }

  function logout() {
    clearToken()
  }

  const isAuthenticated = computed(() => !!token.value)

  return { token, refreshToken, user, setToken, clearToken, isAuthenticated, logout, fetchUser }
})