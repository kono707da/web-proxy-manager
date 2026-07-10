<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell
} from '@/components/ui/table'
import { Loader2, RefreshCw, Zap, Globe, Inbox } from 'lucide-vue-next'
import { listProxies, selectProxy, testDelay } from '@/api/proxy'
import { getStatus } from '@/api/system'

const toast = useToast()

const loading = ref(false)
const proxies = ref([])
const groups = ref([])
const notRunning = ref(false)
// 节点名 → 订阅名映射
const nodeSource = ref({})
// 节点延迟映射：{ [name]: delay }
const delayMap = reactive({})
// 节点测速中状态：{ [name]: boolean }
const testingMap = reactive({})
const batchTesting = ref(false)

// 检查内核是否运行
async function loadStatus() {
  try {
    const s = await getStatus()
    notRunning.value = !s.running
    return !!s.running
  } catch (e) {
    notRunning.value = true
    return false
  }
}

async function loadProxies() {
  const running = await loadStatus()
  if (!running) return
  loading.value = true
  try {
    const data = await listProxies()
    proxies.value = data.proxies || []
    groups.value = data.groups || []
    nodeSource.value = data.node_source || {}
    // 初始化延迟映射：从 history 末尾取最近一次延迟
    proxies.value.forEach((p) => {
      const hist = p.history || []
      const last = hist.length ? hist[hist.length - 1] : null
      delayMap[p.name] = last ? (last.delay ?? 0) : 0
    })
  } catch (e) {
    toast.error('获取代理节点失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

// 切换分组选中节点
async function onSelect(group, name) {
  try {
    await selectProxy(group, name)
    toast.success('节点已切换', `${group} → ${name}`)
    await loadProxies()
  } catch (e) {
    toast.error('切换节点失败', e.response?.data?.detail || e.message)
  }
}

// 测速单个节点
async function onTestDelay(name) {
  testingMap[name] = true
  try {
    const data = await testDelay(name)
    delayMap[name] = data.delay ?? 0
    if (data.delay === 0) {
      toast.warning('测速超时', `节点「${name}」无响应`)
    }
  } catch (e) {
    delayMap[name] = 0
    toast.error('测速失败', `节点「${name}」: ${e.response?.data?.detail || e.message}`)
  } finally {
    testingMap[name] = false
  }
}

// 批量测速所有节点
async function onBatchTest() {
  if (batchTesting.value) return
  batchTesting.value = true
  try {
    await Promise.all(proxies.value.map((p) => onTestDelay(p.name)))
    toast.success('批量测速完成')
  } catch (e) {
    toast.error('批量测速失败', e.message)
  } finally {
    batchTesting.value = false
  }
}

// 延迟颜色：绿 <200 / 黄 <500 / 红 >=500 / 灰 =0超时
function delayColor(delay) {
  if (!delay || delay === 0) return 'text-muted-foreground'
  if (delay < 200) return 'text-emerald-400'
  if (delay < 500) return 'text-yellow-400'
  return 'text-red-400'
}

function delayText(delay) {
  if (!delay || delay === 0) return '超时'
  return `${delay} ms`
}

onMounted(() => {
  loadProxies()
})
</script>

<template>
  <div class="space-y-6">
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">代理节点</h2>
      <div class="flex gap-2">
        <Button variant="secondary" :disabled="loading" @click="loadProxies">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <RefreshCw v-else class="h-4 w-4" />
          刷新
        </Button>
        <Button variant="gold" :disabled="batchTesting || notRunning" @click="onBatchTest">
          <Loader2 v-if="batchTesting" class="h-4 w-4 animate-spin" />
          <Zap v-else class="h-4 w-4" />
          批量测速
        </Button>
      </div>
    </div>

    <!-- 未运行提示 -->
    <Alert v-if="notRunning" variant="destructive">
      <AlertTitle>mihomo 未运行</AlertTitle>
      <AlertDescription>请到「系统设置」启动内核后再管理代理节点。</AlertDescription>
    </Alert>

    <template v-else>
      <!-- 分组区域 -->
      <div class="space-y-4">
        <Card v-for="group in groups" :key="group.name">
          <CardHeader class="pb-3">
            <div class="flex items-center gap-2 flex-wrap">
              <Globe class="h-4 w-4 text-primary" />
              <CardTitle class="text-base">{{ group.name }}</CardTitle>
              <Badge variant="secondary">{{ group.type }}</Badge>
              <Badge v-if="group.now" variant="default">当前: {{ group.now }}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="name in group.all"
                :key="name"
                class="flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-sm transition-colors cursor-pointer"
                :class="name === group.now
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border text-muted-foreground hover:bg-accent hover:text-foreground'"
                @click="onSelect(group.name, name)"
              >
                <span>{{ name }}</span>
                <button
                  type="button"
                  class="ml-1 rounded p-0.5 text-muted-foreground transition-colors hover:text-primary disabled:opacity-50"
                  :disabled="testingMap[name]"
                  @click.stop="onTestDelay(name)"
                >
                  <Loader2 v-if="testingMap[name]" class="h-3.5 w-3.5 animate-spin" />
                  <Zap v-else class="h-3.5 w-3.5" />
                </button>
                <span
                  v-if="delayMap[name] !== undefined"
                  class="text-xs font-medium"
                  :class="delayColor(delayMap[name])"
                >
                  {{ delayText(delayMap[name]) }}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- 节点列表表格 -->
      <Card>
        <CardHeader>
          <CardTitle>全部节点</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="relative rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow class="hover:bg-transparent">
                  <TableHead>名称</TableHead>
                  <TableHead class="w-28">来源订阅</TableHead>
                  <TableHead class="w-24">类型</TableHead>
                  <TableHead class="w-24">UDP</TableHead>
                  <TableHead class="w-24">状态</TableHead>
                  <TableHead class="w-28 text-right">最近延迟</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="p in proxies" :key="p.name">
                  <TableCell class="font-medium">
                    {{ p.name }}
                  </TableCell>
                  <TableCell>
                    <Badge v-if="nodeSource[p.name]" variant="secondary">{{ nodeSource[p.name] }}</Badge>
                    <span v-else class="text-muted-foreground text-xs">—</span>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{{ p.type }}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge :variant="p.udp ? 'success' : 'secondary'">
                      {{ p.udp ? '支持' : '不支持' }}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge :variant="p.alive ? 'success' : 'secondary'">
                      {{ p.alive ? '可用' : '不可用' }}
                    </Badge>
                  </TableCell>
                  <TableCell class="text-right">
                    <span class="font-medium" :class="delayColor(delayMap[p.name])">
                      {{ delayText(delayMap[p.name]) }}
                    </span>
                  </TableCell>
                </TableRow>
                <TableRow v-if="proxies.length === 0 && !loading" class="hover:bg-transparent">
                  <TableCell colspan="6">
                    <div class="flex flex-col items-center justify-center py-10 text-muted-foreground">
                      <Inbox class="h-10 w-10 mb-2 opacity-50" />
                      <span class="text-sm">暂无节点</span>
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
    </template>
  </div>
</template>
