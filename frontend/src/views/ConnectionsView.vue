<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { useConfirm } from '@/composables/use-confirm'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell
} from '@/components/ui/table'
import {
  Loader2, RefreshCw, Trash2, Inbox, ArrowUp, ArrowDown, MemoryStick, Network
} from 'lucide-vue-next'
import { listConnections, closeConnection, closeAllConnections } from '@/api/connection'
import { formatBytes } from '@/lib/format'

const toast = useToast()
const { confirm } = useConfirm()

const loading = ref(false)
const data = ref({ downloadTotal: 0, uploadTotal: 0, connections: [], memory: 0 })
const autoRefresh = ref(true)

let timer = null

async function loadConnections() {
  loading.value = true
  try {
    data.value = await listConnections()
  } catch (e) {
    toast.error('获取连接列表失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

// 静默轮询（不显示 loading、不弹错误，避免刷屏）
async function pollConnections() {
  try {
    data.value = await listConnections()
  } catch (e) {
    // 静默
  }
}

async function onClose(id) {
  try {
    await closeConnection(id)
    toast.success('连接已关闭')
    await loadConnections()
  } catch (e) {
    toast.error('关闭连接失败', e.response?.data?.detail || e.message)
  }
}

async function onCloseAll() {
  const ok = await confirm('确定关闭所有连接？此操作不可撤销。', {
    title: '关闭全部连接',
    type: 'danger'
  })
  if (!ok) return
  try {
    await closeAllConnections()
    toast.success('已关闭所有连接')
    await loadConnections()
  } catch (e) {
    toast.error('关闭全部连接失败', e.response?.data?.detail || e.message)
  }
}

function startTimer() {
  stopTimer()
  timer = setInterval(() => {
    pollConnections()
  }, 3000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

// 自动刷新开关变化
watch(autoRefresh, (val) => {
  if (val) {
    startTimer()
  } else {
    stopTimer()
  }
})

onMounted(() => {
  loadConnections()
  if (autoRefresh.value) startTimer()
})

onUnmounted(() => {
  stopTimer()
})
</script>

<template>
  <div class="space-y-6">
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h2 class="text-2xl font-bold tracking-tight">连接管理</h2>
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-2 rounded-md border border-border px-3 py-1.5">
          <Label for="auto-refresh" class="text-sm cursor-pointer">自动刷新</Label>
          <Switch id="auto-refresh" v-model:checked="autoRefresh" />
        </div>
        <Button variant="secondary" :disabled="loading" @click="loadConnections">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <RefreshCw v-else class="h-4 w-4" />
          刷新
        </Button>
        <Button variant="destructive" @click="onCloseAll">
          <Trash2 class="h-4 w-4" />
          关闭全部
        </Button>
      </div>
    </div>

    <!-- 顶部统计 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <ArrowUp class="h-3 w-3 text-emerald-400" /> 总上传
          </div>
          <div class="mt-1 text-xl font-bold text-emerald-400">{{ formatBytes(data.uploadTotal) }}</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <ArrowDown class="h-3 w-3 text-sky-400" /> 总下载
          </div>
          <div class="mt-1 text-xl font-bold text-sky-400">{{ formatBytes(data.downloadTotal) }}</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Network class="h-3 w-3" /> 当前连接
          </div>
          <div class="mt-1 text-xl font-bold">{{ data.connections.length }}</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
            <MemoryStick class="h-3 w-3" /> 内存占用
          </div>
          <div class="mt-1 text-xl font-bold text-primary">{{ formatBytes(data.memory) }}</div>
        </CardContent>
      </Card>
    </div>

    <!-- 连接列表 -->
    <Card>
      <CardContent class="pt-6">
        <div class="relative rounded-md border border-border overflow-auto">
          <Table>
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead class="w-24">ID</TableHead>
                <TableHead class="min-w-[160px]">目标主机</TableHead>
                <TableHead class="w-24">网络</TableHead>
                <TableHead class="min-w-[140px]">源地址</TableHead>
                <TableHead class="min-w-[140px]">规则</TableHead>
                <TableHead class="min-w-[120px]">链路</TableHead>
                <TableHead class="text-right w-24">上传</TableHead>
                <TableHead class="text-right w-24">下载</TableHead>
                <TableHead class="w-16 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="conn in data.connections" :key="conn.id">
                <TableCell class="font-mono text-xs text-muted-foreground" :title="conn.id">
                  {{ conn.id?.slice(0, 8) }}
                </TableCell>
                <TableCell class="font-medium">{{ conn.metadata?.host || conn.metadata?.destinationIP || '—' }}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{{ conn.metadata?.network || '—' }}</Badge>
                </TableCell>
                <TableCell class="text-muted-foreground text-sm">
                  {{ conn.metadata?.sourceIP }}:{{ conn.metadata?.sourcePort }}
                </TableCell>
                <TableCell class="text-muted-foreground text-sm">
                  {{ conn.rule }}<span v-if="conn.rulePayload"> ({{ conn.rulePayload }})</span>
                </TableCell>
                <TableCell class="text-muted-foreground text-sm">
                  {{ (conn.chains || []).join(' → ') }}
                </TableCell>
                <TableCell class="text-right text-emerald-400 text-sm">{{ formatBytes(conn.upload) }}</TableCell>
                <TableCell class="text-right text-sky-400 text-sm">{{ formatBytes(conn.download) }}</TableCell>
                <TableCell class="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8 text-destructive hover:text-destructive"
                    @click="onClose(conn.id)"
                  >
                    <Trash2 class="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="data.connections.length === 0 && !loading" class="hover:bg-transparent">
                <TableCell colspan="9">
                  <div class="flex flex-col items-center justify-center py-10 text-muted-foreground">
                    <Inbox class="h-10 w-10 mb-2 opacity-50" />
                    <span class="text-sm">暂无连接</span>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <div
            v-if="loading"
            class="absolute inset-0 flex items-center justify-center rounded-md bg-background/60 backdrop-blur-sm"
          >
            <Loader2 class="h-5 w-5 animate-spin text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
