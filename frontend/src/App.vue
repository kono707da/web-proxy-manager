<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSystemStore } from '@/stores/system'
import { Button } from '@/components/ui/button'
import { Toaster } from '@/components/ui/toast'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import {
  LayoutDashboard, Globe, Rss, Route, Network,
  Gauge, Database, Settings, LogOut, ShieldCheck,
  ScrollText, Activity, Zap
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const systemStore = useSystemStore()

const isLoginPage = computed(() => route.path === '/login')

const navItems = [
  { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { path: '/proxies', label: '代理节点', icon: Globe },
  { path: '/subscriptions', label: '订阅管理', icon: Rss },
  { path: '/rules', label: '规则路由', icon: Route },
  { path: '/connections', label: '连接管理', icon: Network },
  { path: '/limits', label: '限速控制', icon: Gauge },
  { path: '/quotas', label: '流量配额', icon: Database },
  { path: '/logs', label: '系统日志', icon: ScrollText },
  { path: '/settings', label: '系统设置', icon: Settings }
]

function navigate(path) {
  router.push(path)
}

function logout() {
  authStore.logout()
  router.push('/login')
}

// 登录后启动状态轮询，登出后停止
watch(() => authStore.isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    systemStore.startPolling(5000)
  } else {
    systemStore.stopPolling()
  }
}, { immediate: true })

onMounted(() => {
  if (authStore.isLoggedIn) {
    systemStore.startPolling(5000)
  }
})

onUnmounted(() => {
  systemStore.stopPolling()
})
</script>

<template>
  <div v-if="isLoginPage">
    <router-view />
  </div>
  <div v-else class="flex h-screen flex-col bg-background text-foreground">
    <header class="glass-dark flex h-14 items-center justify-between border-b border-border px-6">
      <div class="flex items-center gap-2">
        <ShieldCheck class="h-6 w-6 text-primary" />
        <span class="text-lg font-bold text-gold-gradient">Proxy Manager</span>
      </div>
      <div class="flex items-center gap-4">
        <!-- 代理状态指示器 -->
        <div class="flex items-center gap-2 rounded-md border border-border px-3 py-1">
          <Activity
            class="h-3.5 w-3.5"
            :class="systemStore.running ? 'text-emerald-400' : 'text-muted-foreground'"
          />
          <span v-if="systemStore.running" class="text-xs text-emerald-400 font-medium">运行中</span>
          <span v-else class="text-xs text-muted-foreground font-medium">已停止</span>
          <template v-if="systemStore.running">
            <span class="text-xs text-muted-foreground">|</span>
            <span class="text-xs text-muted-foreground uppercase">{{ systemStore.mode || '—' }}</span>
            <span class="text-xs text-muted-foreground">|</span>
            <Zap class="h-3 w-3 text-primary" />
            <span class="text-xs text-primary font-medium truncate max-w-[160px]" :title="systemStore.currentProxy">
              {{ systemStore.currentProxy || '未选择' }}
            </span>
          </template>
        </div>
        <span class="text-sm text-muted-foreground">{{ authStore.username }}</span>
        <Button variant="ghost" size="sm" @click="logout">
          <LogOut class="h-4 w-4" />退出
        </Button>
      </div>
    </header>
    <div class="flex flex-1 overflow-hidden">
      <aside class="glass-dark w-56 overflow-y-auto border-r border-border">
        <nav class="space-y-1 p-3">
          <div
            v-for="item in navItems"
            :key="item.path"
            class="nav-item"
            :class="{ 'nav-item-active': route.path === item.path }"
            @click="navigate(item.path)"
          >
            <component :is="item.icon" class="h-4 w-4" />
            <span>{{ item.label }}</span>
          </div>
        </nav>
      </aside>
      <main class="flex-1 overflow-auto p-6">
        <router-view />
      </main>
    </div>
    <Toaster />
    <ConfirmDialog />
  </div>
</template>
