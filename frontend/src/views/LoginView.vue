<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/components/ui/toast/use-toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { ShieldCheck, Eye, EyeOff, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const toast = useToast()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)

async function onLogin() {
  if (!username.value || !password.value) {
    toast.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await authStore.login(username.value, password.value)
    toast.success('登录成功')
    const redirect = route.query.redirect
    router.push(redirect || '/dashboard')
  } catch (e) {
    toast.error('登录失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-background p-4">
    <Card class="glass-dark w-full max-w-md">
      <CardHeader class="space-y-3 text-center">
        <div class="flex justify-center">
          <div class="flex h-14 w-14 items-center justify-center rounded-xl border border-primary/30 bg-primary/10">
            <ShieldCheck class="h-7 w-7 text-primary" />
          </div>
        </div>
        <div class="space-y-1">
          <CardTitle class="text-2xl text-gold-gradient">Proxy Manager</CardTitle>
          <CardDescription>代理流量管理控制台</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <form class="space-y-4" @submit.prevent="onLogin">
          <div class="space-y-2">
            <Label for="login-username">用户名</Label>
            <Input
              id="login-username"
              v-model="username"
              placeholder="admin"
              autocomplete="username"
            />
          </div>
          <div class="space-y-2">
            <Label for="login-password">密码</Label>
            <div class="relative">
              <Input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="admin123"
                autocomplete="current-password"
                class="pr-10"
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                @click="showPassword = !showPassword"
              >
                <Eye v-if="!showPassword" class="h-4 w-4" />
                <EyeOff v-else class="h-4 w-4" />
              </button>
            </div>
          </div>
          <Button type="submit" variant="gold" class="w-full" :disabled="loading">
            <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
            {{ loading ? '登录中...' : '登录' }}
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>
