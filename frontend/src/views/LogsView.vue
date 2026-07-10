<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell
} from '@/components/ui/table'
import { Loader2, RefreshCw, ScrollText, Server, Inbox, Search, Pause, Play } from 'lucide-vue-next'
import { getAllLogs } from '@/api/log'

const toast = useToast()

const loading = ref(false)
const activeTab = ref('app') // app / mihomo
const appLogs = ref([])
const mihomoLogs = ref([])
const mihomoMsg = ref('')
// 过滤参数
const filter = reactive({
  tail: 300,
  level: '',
  keyword: ''
})
// 自动刷新
const autoRefresh = ref(true)
let timer = null
// 日志容器引用，用于自动滚动到底部
const logContainerRef = ref(null)

const levelOptions = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR']

async function loadLogs() {
  loading.value = true
  try {
    const params = { tail: filter.tail }
    if (filter.level) params.level = filter.level
    if (filter.keyword) params.keyword = filter.keyword
    const data = await getAllLogs(params)
    appLogs.value = data.app?.logs || []
    mihomoLogs.value = data.mihomo?.logs || []
    mihomoMsg.value = data.mihomo?.message || ''
    if (autoRefresh.value) {
      await nextTick()
      scrollToBottom()
    }
  } catch (e) {
    toast.error('获取日志失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function scrollToBottom() {
  const el = logContainerRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startTimer()
  } else {
    stopTimer()
  }
}

function startTimer() {
  stopTimer()
  timer = setInterval(loadLogs, 3000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

// 应用日志按级别着色
function appLogLevelClass(level) {
  switch (level) {
    case 'ERROR':
    case 'CRITICAL':
      return 'text-red-400'
    case 'WARNING':
      return 'text-yellow-400'
    case 'INFO':
      return 'text-emerald-400'
    case 'DEBUG':
      return 'text-muted-foreground'
    default:
      return 'text-muted-foreground'
  }
}

// mihomo 日志行着色（简单关键词匹配）
function mihomoLineClass(line) {
  if (/error|fail|fatal/i.test(line)) return 'text-red-400'
  if (/warn/i.test(line)) return 'text-yellow-400'
  if (/info/i.test(line)) return 'text-emerald-400'
  return 'text-muted-foreground'
}

const currentLogs = computed(() => activeTab.value === 'app' ? appLogs.value : mihomoLogs.value)

onMounted(() => {
  loadLogs()
  startTimer()
})

onUnmounted(() => {
  stopTimer()
})
</script>

<template>
  <div class="space-y-6">
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">系统日志</h2>
      <div class="flex items-center gap-2">
        <Button variant="secondary" :disabled="loading" @click="loadLogs">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <RefreshCw v-else class="h-4 w-4" />
          刷新
        </Button>
        <Button
          :variant="autoRefresh ? 'gold' : 'secondary'"
          @click="toggleAutoRefresh"
        >
          <Pause v-if="autoRefresh" class="h-4 w-4" />
          <Play v-else class="h-4 w-4" />
          {{ autoRefresh ? '暂停自动刷新' : '恢复自动刷新' }}
        </Button>
      </div>
    </div>

    <!-- 过滤栏 -->
    <Card>
      <CardContent class="pt-6">
        <div class="flex flex-wrap items-end gap-4">
          <div class="flex flex-col gap-1.5">
            <Label class="text-xs">条数</Label>
            <Input
              v-model="filter.tail"
              type="number"
              min="50"
              max="2000"
              class="w-28"
              @change="loadLogs"
            />
          </div>
          <div class="flex flex-col gap-1.5" v-if="activeTab === 'app'">
            <Label class="text-xs">最低级别</Label>
            <div class="flex gap-1">
              <Button
                v-for="lvl in levelOptions"
                :key="lvl"
                size="sm"
                :variant="filter.level === lvl ? 'gold' : 'secondary'"
                @click="filter.level = lvl; loadLogs()"
              >
                {{ lvl || '全部' }}
              </Button>
            </div>
          </div>
          <div class="flex flex-col gap-1.5 flex-1 min-w-[200px]">
            <Label class="text-xs">关键词</Label>
            <div class="relative">
              <Search class="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                v-model="filter.keyword"
                placeholder="搜索关键词..."
                class="pl-8"
                @keyup.enter="loadLogs"
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Tab 切换 -->
    <div class="flex gap-2">
      <Button
        :variant="activeTab === 'app' ? 'gold' : 'secondary'"
        @click="activeTab = 'app'"
      >
        <Server class="h-4 w-4" />
        应用日志
        <Badge variant="secondary" class="ml-1">{{ appLogs.length }}</Badge>
      </Button>
      <Button
        :variant="activeTab === 'mihomo' ? 'gold' : 'secondary'"
        @click="activeTab = 'mihomo'"
      >
        <ScrollText class="h-4 w-4" />
        mihomo 日志
        <Badge variant="secondary" class="ml-1">{{ mihomoLogs.length }}</Badge>
      </Button>
    </div>

    <!-- 日志内容 -->
    <Card>
      <CardContent class="p-0">
        <div
          ref="logContainerRef"
          class="h-[480px] overflow-auto rounded-md bg-zinc-950/80 p-4 font-mono text-xs leading-relaxed"
        >
          <!-- 应用日志 -->
          <template v-if="activeTab === 'app'">
            <div v-if="appLogs.length === 0 && !loading" class="flex flex-col items-center justify-center py-10 text-muted-foreground">
              <Inbox class="h-10 w-10 mb-2 opacity-50" />
              <span>暂无应用日志</span>
            </div>
            <div
              v-for="(log, i) in appLogs"
              :key="i"
              class="flex gap-2 py-0.5 border-b border-zinc-800/50"
            >
              <span class="text-muted-foreground shrink-0">{{ log.timestamp }}</span>
              <span class="shrink-0 font-bold w-16" :class="appLogLevelClass(log.level)">{{ log.level }}</span>
              <span class="text-sky-300/70 shrink-0 max-w-[180px] truncate" :title="log.logger">{{ log.logger }}</span>
              <span class="text-zinc-200 break-all">{{ log.message }}</span>
            </div>
          </template>

          <!-- mihomo 日志 -->
          <template v-else>
            <div v-if="mihomoMsg" class="text-yellow-400 py-2">{{ mihomoMsg }}</div>
            <div v-else-if="mihomoLogs.length === 0 && !loading" class="flex flex-col items-center justify-center py-10 text-muted-foreground">
              <Inbox class="h-10 w-10 mb-2 opacity-50" />
              <span>暂无 mihomo 日志</span>
            </div>
            <div
              v-for="(log, i) in mihomoLogs"
              :key="i"
              class="py-0.5 break-all"
              :class="mihomoLineClass(log.line)"
            >
              {{ log.line }}
            </div>
          </template>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
