import axios from 'axios'

const client = axios.create({
  baseURL: '',
  timeout: 15000
})

// 请求拦截器：注入 token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('proxy_manager_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (err) => Promise.reject(err))

// 响应拦截器：401 清除登录态并跳转登录
client.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const status = error.response?.status
    if (status === 401) {
      localStorage.removeItem('proxy_manager_token')
      localStorage.removeItem('proxy_manager_user')
      // 避免在登录页循环跳转
      if (!window.location.hash.includes('/login') && !window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default client
