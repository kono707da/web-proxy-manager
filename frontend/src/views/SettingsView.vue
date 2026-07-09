<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { useConfirm } from '@/composables/use-confirm'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Loader2, Play, Square, RotateCw, RefreshCw } from 'lucide-vue-next'
import {
  getStatus, startCore, stopCore, restartCore, reloadCore, updateMode, updateLogLevel
} from '@/api/system'
import { formatDuration } from '@/lib/format'

const toast = useToast()
const { confirm } = useConfirm()

const loading = ref(false)
const status = ref({})
const logLevel = ref('info')
// 各操作独立 loading 状态
const action = reactive({
  start: false,
  stop: false,
  restart: false,
  reload: false,
  mode: false,
  logLevel: false
})

const modes = [
  { value: 'rule', label: '规则模式' },
  { value: 'global', label: '全局模式' },
  { value: 'direct', label: '直连模式' }
]

const logLevels = ['debug', 'info', 'warning', 'error', 'silent']

async function loadStatus() {
  loading.value = true
  try {
    status.value = await getStatus()
    logLevel.value = status.value.log_level || 'info'
  } catch (e) {
    toast.error('获取内核状态失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function onStart() {
  action.start = true
  try {
    const res = await startCore()
    toast.success('启动成功', res.message)
    await loadStatus()
  } catch (e) {
    toast.error('启动内核失败', e.response?.data?.detail || e.message)
  } finally {
    action.start = false
  }
}

async function onStop() {
  const ok = await confirm('确定停止 mihomo 内核？停止后代理流量将中断。', {
    title: '停止内核',
    type: 'danger'
  })
  if (!ok) return
  action.stop = true
  try {
    const res = await stopCore()
    toast.success('已停止', res.message)
    await loadStatus()
  } catch (e) {
    toast.error('停止内核失败', e.response?.data?.detail || e.message)
  } finally {
    action.stop = false
  }
}

async function onRestart() {
  const ok = await confirm('确定重启 mihomo 内核？重启期间代理流量会短暂中断。', {
    title: '重启内核',
    type: 'warning'
  })
  if (!ok) return
  action.restart = true
  try {
    const res = await restartCore()
    toast.success('重启成功', res.message)
    await loadStatus()
  } catch (e) {
    toast.error('重启内核失败', e.response?.data?.detail || e.message)
  } finally {
    action.restart = false
  }
}

async function onReload() {
  action.reload = true
  try {
    const res = await reloadCore()
    toast.success('配置已重载', res.message)
    await loadStatus()
  } catch (e) {
    toast.error('重载配置失败', e.response?.data?.detail || e.message)
  } finally {
    action.reload = false
  }
}

async function onModeChange(mode) {
  action.mode = true
  try {
    const res = await updateMode(mode)
    toast.success('模式已切换', res.message)
    await loadStatus()
  } catch (e) {
    toast.error('切换代理模式失败', e.response?.data?.detail || e.message)
  } finally {
    action.mode = false
  }
}

async function onLogLevelChange(level) {
  action.logLevel = true
  try {
    const res = await updateLogLevel(level)
    toast.success('日志级别已切换', res.message)
    await loadStatus()
  } catch (e) {
    toast.error('切换日志级别失败', e.response?.data?.detail || e.message)
    // 失败时回退到当前状态
    logLevel.value = status.value.log_level || 'info'
  } finally {
    action.logLevel = false
  }
}

onMounted(() => {
  loadStatus()
})
</script>

<template>
  <div class="space-y-6">
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">系统设置</h2>
      <Button variant="secondary" :disabled="loading" @click="loadStatus">
        <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
        <RefreshCw v-else class="h-4 w-4" />
        刷新
      </Button>
    </div>

    <!-- 内核错误告警 -->
    <Alert v-if="status.last_error" variant="destructive">
      <AlertTitle>内核错误</AlertTitle>
      <AlertDescription>{{ status.last_error }}</AlertDescription>
    </Alert>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- 内核控制 -->
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle>内核控制</CardTitle>
            <Badge :variant="status.running ? 'success' : 'secondary'">
              {{ status.running ? '运行中' : '已停止' }}
            </Badge>
          </div>
          <CardDescription>启动、停止、重启 mihomo 内核</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="flex flex-wrap gap-2">
            <Button
              variant="gold"
              :disabled="status.running || action.start"
              @click="onStart"
            >
              <Loader2 v-if="action.start" class="h-4 w-4 animate-spin" />
              <Play v-else class="h-4 w-4" />
              启动
            </Button>
            <Button
              variant="destructive"
              :disabled="!status.running || action.stop"
              @click="onStop"
            >
              <Loader2 v-if="action.stop" class="h-4 w-4 animate-spin" />
              <Square v-else class="h-4 w-4" />
              停止
            </Button>
            <Button
              variant="secondary"
              :disabled="action.restart"
              @click="onRestart"
            >
              <Loader2 v-if="action.restart" class="h-4 w-4 animate-spin" />
              <RotateCw v-else class="h-4 w-4" />
              重启
            </Button>
            <Button
              variant="secondary"
              :disabled="!status.running || action.reload"
              @click="onReload"
            >
              <Loader2 v-if="action.reload" class="h-4 w-4 animate-spin" />
              <RefreshCw v-else class="h-4 w-4" />
              重载配置
            </Button>
          </div>
        </CardContent>
      </Card>

      <!-- 代理模式 -->
      <Card>
        <CardHeader>
          <CardTitle>代理模式</CardTitle>
          <CardDescription>切换 mihomo 的流量代理模式</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="flex flex-wrap gap-2">
            <Button
              v-for="m in modes"
              :key="m.value"
              :variant="status.mode === m.value ? 'gold' : 'secondary'"
              :disabled="action.mode"
              @click="onModeChange(m.value)"
            >
              <Loader2 v-if="action.mode" class="h-4 w-4 animate-spin" />
              {{ m.label }}
            </Button>
          </div>
        </CardContent>
      </Card>

      <!-- 日志级别 -->
      <Card>
        <CardHeader>
          <CardTitle>日志级别</CardTitle>
          <CardDescription>控制 mihomo 日志输出详细程度</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="flex items-center gap-3">
            <Select
              :model-value="logLevel"
              :disabled="action.logLevel"
              @update:model-value="onLogLevelChange"
            >
              <SelectTrigger class="w-48">
                <SelectValue placeholder="选择日志级别" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="lvl in logLevels" :key="lvl" :value="lvl">
                  {{ lvl }}
                </SelectItem>
              </SelectContent>
            </Select>
            <Loader2 v-if="action.logLevel" class="h-4 w-4 animate-spin text-primary" />
          </div>
        </CardContent>
      </Card>

      <!-- 端口信息 -->
      <Card>
        <CardHeader>
          <CardTitle>端口信息</CardTitle>
          <CardDescription>当前内核监听端口与配置（只读）</CardDescription>
        </CardHeader>
        <CardContent class="space-y-2">
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">混合端口</span>
            <span class="font-medium">{{ status.mixed_port ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">API 端口</span>
            <span class="font-medium">{{ status.api_port ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">代理模式</span>
            <span class="font-medium uppercase">{{ status.mode ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">日志级别</span>
            <span class="font-medium">{{ status.log_level ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">PID</span>
            <span class="font-medium">{{ status.pid ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">运行时长</span>
            <span class="font-medium">{{ formatDuration(status.uptime) }}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
