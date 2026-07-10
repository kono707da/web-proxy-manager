import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { requiresAuth: true } },
  { path: '/proxies', name: 'proxies', component: () => import('../views/ProxiesView.vue'), meta: { requiresAuth: true } },
  { path: '/subscriptions', name: 'subscriptions', component: () => import('../views/SubscriptionsView.vue'), meta: { requiresAuth: true } },
  { path: '/rules', name: 'rules', component: () => import('../views/RulesView.vue'), meta: { requiresAuth: true } },
  { path: '/devices', name: 'devices', component: () => import('../views/DevicesView.vue'), meta: { requiresAuth: true } },
  { path: '/connections', name: 'connections', component: () => import('../views/ConnectionsView.vue'), meta: { requiresAuth: true } },
  { path: '/limits', name: 'limits', component: () => import('../views/LimitsView.vue'), meta: { requiresAuth: true } },
  { path: '/quotas', name: 'quotas', component: () => import('../views/QuotasView.vue'), meta: { requiresAuth: true } },
  { path: '/logs', name: 'logs', component: () => import('../views/LogsView.vue'), meta: { requiresAuth: true } },
  { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue'), meta: { requiresAuth: true } },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, _from, next) => {
  if (!to.meta.requiresAuth) return next()
  const authStore = useAuthStore()
  if (!authStore.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }
  next()
})

export default router
