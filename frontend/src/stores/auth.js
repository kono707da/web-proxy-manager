import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, getMe } from '@/api/auth'

const TOKEN_KEY = 'proxy_manager_token'
const USER_KEY = 'proxy_manager_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const userInfo = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => !!userInfo.value?.is_admin)
  const username = computed(() => userInfo.value?.username || '')

  function restore() {
    const t = localStorage.getItem(TOKEN_KEY)
    const u = localStorage.getItem(USER_KEY)
    if (t) token.value = t
    if (u) {
      try { userInfo.value = JSON.parse(u) } catch { userInfo.value = null }
    }
  }

  function setAuth(t, info) {
    token.value = t
    userInfo.value = info
    localStorage.setItem(TOKEN_KEY, t)
    localStorage.setItem(USER_KEY, JSON.stringify(info))
  }

  async function login(username, password) {
    const data = await apiLogin(username, password)
    setAuth(data.access_token, data.user)
    return data
  }

  async function fetchMe() {
    try {
      const me = await getMe()
      userInfo.value = me
      localStorage.setItem(USER_KEY, JSON.stringify(me))
      return me
    } catch {
      clear()
      return null
    }
  }

  function clear() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  function logout() {
    clear()
  }

  return { token, userInfo, isLoggedIn, isAdmin, username, restore, setAuth, login, fetchMe, logout, clear }
})
