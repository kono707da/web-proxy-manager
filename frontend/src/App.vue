<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { Toaster } from '@/components/ui/toast'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import {
  LayoutDashboard, Globe, Rss, Route, Network,
  Gauge, Database, Settings, LogOut, ShieldCheck
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isLoginPage = computed(() => route.path === '/login')

const navItems = [
  { path: '/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { path: '/proxies', label: '代理节点', icon: Globe },
  { path: '/subscriptions', label: '订阅管理', icon: Rss },
  { path: '/rules', label: '规则路由', icon: Route },
  { path: '/connections', label: '连接管理', icon: Network },
  { path: '/limits', label: '限速控制', icon: Gauge },
  { path: '/quotas', label: '流量配额', icon: Database },
  { path: '/settings', label: '系统设置', icon: Settings }
]

function navigate(path) {
  router.push(path)
}

function logout() {
  authStore.logout()
  router.push('/login')
}
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
      <div class="flex items-center gap-3">
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
