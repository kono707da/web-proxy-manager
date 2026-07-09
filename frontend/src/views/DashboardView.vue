<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell
} from '@/components/ui/table'
import {
  Loader2, RefreshCw, Activity, Cpu, MemoryStick,
  ArrowUp, ArrowDown, Server, Inbox
} from 'lucide-vue-next'
import { getStatus, getInfo } from '@/api/system'
import { getRealtimeTraffic, getMemoryUsage, listTrafficStats } from '@/api/traffic'
import { formatBytes, formatSpeed, formatDuration, formatDateTime } from '@/lib/format'

const toast = useToast()

const loading = ref(false)
const status = ref({})
const info = ref({})
const traffic = ref({ up: 0, down: 0 })
const memory = ref({ inuse: 0 })
const stats = ref([])

let trafficTimer = null

async function loadStatus() {
  try {
    status.value = await getStatus()
  } catch (e) {
    toast.error('获取内核状态失败', e.response?.data?.detail || e.message)
  }
}

async function loadInfo() {
  try {
    info.value = await getInfo()
  } catch (e) {
    toast.error('获取系统资源信息失败', e.response?.data?.detail || e.message)
  }
}

async function loadTraffic() {
  try {
    traffic.value = await getRealtimeTraffic()
  } catch (e) {
    // 轮询错误静默处理，避免刷屏
  }
}

async function loadMemory() {
  try {
    memory.value = await getMemoryUsage()
  } catch (e) {
    // 内存接口可能未启用，静默处理
  }
}

async function loadStats() {
  try {
    const data = await listTrafficStats()
    stats.value = Array.isArray(data) ? data : (data?.items || [])
  } catch (e) {
    toast.error('获取客户端流量统计失败', e.response?.data?.detail || e.message)
  }
}

async function refreshAll() {
  loading.value = true
  await Promise.all([loadStatus(), loadInfo(), loadMemory(), loadTraffic(), loadStats()])
  loading.value = false
}

onMounted(() => {
  refreshAll()
  // 每 2 秒轮询实时流量与内存
  trafficTimer = setInterval(() => {
    loadTraffic()
    loadMemory()
  }, 2000)
})

onUnmounted(() => {
  if (trafficTimer) {
    clearInterval(trafficTimer)
    trafficTimer = null
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">仪表盘</h2>
      <Button variant="secondary" :disabled="loading" @click="refreshAll">
        <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
        <RefreshCw v-else class="h-4 w-4" />
        刷新
      </Button>
    </div>

    <!-- 状态卡片网格 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 内核状态 -->
      <Card>
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between">
            <CardTitle class="text-sm font-medium text-muted-foreground">内核状态</CardTitle>
            <Server class="h-4 w-4 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-muted-foreground text-sm">运行状态</span>
            <Badge :variant="status.running ? 'success' : 'secondary'">
              {{ status.running ? '运行中' : '已停止' }}
            </Badge>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">PID</span>
            <span class="font-medium">{{ status.pid ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">版本</span>
            <span class="font-medium">{{ status.version ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">运行时长</span>
            <span class="font-medium">{{ formatDuration(status.uptime) }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">代理模式</span>
            <span class="font-medium uppercase">{{ status.mode ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">混合端口</span>
            <span class="font-medium">{{ status.mixed_port ?? '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">API 端口</span>
            <span class="font-medium">{{ status.api_port ?? '—' }}</span>
          </div>
        </CardContent>
      </Card>

      <!-- 实时流量 -->
      <Card>
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between">
            <CardTitle class="text-sm font-medium text-muted-foreground">实时流量</CardTitle>
            <Activity class="h-4 w-4 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent class="space-y-3">
          <div>
            <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ArrowUp class="h-3 w-3 text-emerald-400" /> 上传
            </div>
            <div class="text-2xl font-bold text-emerald-400">{{ formatSpeed(traffic.up) }}</div>
          </div>
          <div>
            <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ArrowDown class="h-3 w-3 text-sky-400" /> 下载
            </div>
            <div class="text-2xl font-bold text-sky-400">{{ formatSpeed(traffic.down) }}</div>
          </div>
        </CardContent>
      </Card>

      <!-- 内核内存 -->
      <Card>
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between">
            <CardTitle class="text-sm font-medium text-muted-foreground">内核内存</CardTitle>
            <MemoryStick class="h-4 w-4 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold text-primary">{{ formatBytes(memory.inuse) }}</div>
          <div class="mt-1 text-xs text-muted-foreground">mihomo 当前占用</div>
        </CardContent>
      </Card>

      <!-- 系统资源 -->
      <Card>
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between">
            <CardTitle class="text-sm font-medium text-muted-foreground">系统资源</CardTitle>
            <Cpu class="h-4 w-4 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent class="space-y-2">
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">CPU</span>
            <span class="font-medium">{{ info.cpu_percent ?? '—' }}%</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">内存</span>
            <span class="font-medium">{{ info.memory_mb != null ? info.memory_mb.toFixed(1) + ' MB' : '—' }}</span>
          </div>
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted-foreground">磁盘</span>
            <span class="font-medium">{{ info.disk_mb != null ? info.disk_mb.toFixed(1) + ' MB' : '—' }}</span>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 内核错误告警 -->
    <Alert v-if="status.last_error" variant="destructive">
      <AlertTitle>内核错误</AlertTitle>
      <AlertDescription>{{ status.last_error }}</AlertDescription>
    </Alert>

    <!-- 客户端流量统计 -->
    <Card>
      <CardHeader>
        <CardTitle>客户端流量统计</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="relative rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead>客户端 IP</TableHead>
                <TableHead class="text-right">上传</TableHead>
                <TableHead class="text-right">下载</TableHead>
                <TableHead class="text-right">总量</TableHead>
                <TableHead class="text-right">最后活跃</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="row in stats" :key="row.client_ip">
                <TableCell class="font-medium">{{ row.client_ip }}</TableCell>
                <TableCell class="text-right text-emerald-400">{{ formatBytes(row.upload_total) }}</TableCell>
                <TableCell class="text-right text-sky-400">{{ formatBytes(row.download_total) }}</TableCell>
                <TableCell class="text-right font-medium">{{ formatBytes(row.total_bytes) }}</TableCell>
                <TableCell class="text-right text-muted-foreground">{{ formatDateTime(row.last_seen) }}</TableCell>
              </TableRow>
              <TableRow v-if="stats.length === 0 && !loading" class="hover:bg-transparent">
                <TableCell colspan="5">
                  <div class="flex flex-col items-center justify-center py-10 text-muted-foreground">
                    <Inbox class="h-10 w-10 mb-2 opacity-50" />
                    <span class="text-sm">暂无流量统计</span>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
