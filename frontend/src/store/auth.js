import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || '')
  const isAdmin = computed(() => userRole.value === 'admin')
  const isAnalyst = computed(() => userRole.value === 'analyst')

  const login = async (credentials) => {
    const response = await apiLogin(credentials)
    token.value = response.access_token
    user.value = response.user
    localStorage.setItem('token', response.access_token)
    return response
  }

  const register = async (userData) => {
    const response = await apiRegister(userData)
    return response
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  const fetchUser = async () => {
    if (!token.value) return
    try {
      const response = await getCurrentUser()
      user.value = response
    } catch (error) {
      logout()
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    userRole,
    isAdmin,
    isAnalyst,
    login,
    register,
    logout,
    fetchUser
  }
})
