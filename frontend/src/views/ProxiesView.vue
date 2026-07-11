<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from '@/components/ui/select'
import { Loader2, RefreshCw, Zap, Globe, Inbox, Monitor, Check, Wifi, WifiOff } from 'lucide-vue-next'
import { listProxies, testDelay } from '@/api/proxy'
import { listDevices, updateDevice } from '@/api/device'
import { listSubscriptions } from '@/api/subscription'
import { getStatus } from '@/api/system'

const toast = useToast()

const loading = ref(false)
const proxies = ref([])
const notRunning = ref(false)
// 节点名 → 订阅名映射
const nodeSource = ref({})
// 节点延迟映射
const delayMap = reactive({})
// 节点测速中状态
const testingMap = reactive({})
const batchTesting = ref(false)

// 设备与订阅
const devices = ref([])
const subscriptions = ref([])
const selectedDeviceId = ref('') // 字符串，给 Select 用
const selectedSubId = ref('all') // 'all' 或订阅 id 字符串

// 计算属性：当前选中设备对象
const selectedDevice = computed(() =>
  devices.value.find((d) => String(d.id) === selectedDeviceId.value) || null
)

// 过滤后的节点列表：按订阅筛选
const filteredProxies = computed(() => {
  if (selectedSubId.value === 'all') return proxies.value
  const sub = subscriptions.value.find((s) => String(s.id) === selectedSubId.value)
  if (!sub) return proxies.value
  return proxies.value.filter((p) => nodeSource.value[p.name] === sub.name)
})

// 设备已分配的节点名
const assignedNode = computed(() => selectedDevice.value?.proxy_name || '')

async function loadStatus() {
  try {
    const s = await getStatus()
    notRunning.value = !s.running
    return !!s.running
  } catch {
    notRunning.value = true
    return false
  }
}

async function loadDevices() {
  try {
    const list = await listDevices()
    devices.value = list.filter((d) => d.enabled)
    // 默认选中第一个设备
    if (!selectedDeviceId.value && devices.value.length > 0) {
      selectedDeviceId.value = String(devices.value[0].id)
    }
  } catch {
    // ignore
  }
}

async function loadSubscriptions() {
  try {
    subscriptions.value = await listSubscriptions()
  } catch {
    // ignore
  }
}

async function loadProxies() {
  const running = await loadStatus()
  if (!running) return
  loading.value = true
  try {
    const data = await listProxies()
    proxies.value = data.proxies || []
    nodeSource.value = data.node_source || {}
    proxies.value.forEach((p) => {
      const hist = p.history || []
      const last = hist.length ? hist[hist.length - 1] : null
      delayMap[p.name] = last ? (last.delay ?? 0) : null
    })
  } catch (e) {
    toast.error('获取代理节点失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

// 点击节点 → 为选中设备分配该节点
async function onAssignNode(nodeName) {
  if (!selectedDevice.value) {
    toast.warning('请先选择设备', '在节点列表上方选择要配置的设备')
    return
  }
  const dev = selectedDevice.value
  // 如果已经分配了同一个节点，不重复操作
  if (dev.proxy_name === nodeName) {
    toast.info('该设备已使用此节点', `${dev.name} → ${nodeName}`)
    return
  }
  try {
    await updateDevice(dev.id, { proxy_name: nodeName })
    // 更新本地设备列表
    dev.proxy_name = nodeName
    toast.success('节点已分配', `${dev.name} → ${nodeName}`)
  } catch (e) {
    toast.error('分配节点失败', e.response?.data?.detail || e.message)
  }
}

// 测速单个节点（超时静默处理，仅更新延迟显示）
async function onTestDelay(name) {
  testingMap[name] = true
  try {
    const data = await testDelay(name)
    delayMap[name] = data.delay ?? 0
  } catch (e) {
    delayMap[name] = 0
    toast.error('测速失败', `节点「${name}」: ${e.response?.data?.detail || e.message}`)
  } finally {
    testingMap[name] = false
  }
}

// 批量测速（限制并发为 5，避免 mihomo 同时收到过多请求导致排队超时）
async function onBatchTest() {
  if (batchTesting.value) return
  batchTesting.value = true
  const nodes = filteredProxies.value.map((p) => p.name)
  const CONCURRENCY = 5
  let index = 0
  async function worker() {
    while (index < nodes.length) {
      const i = index++
      await onTestDelay(nodes[i])
    }
  }
  try {
    await Promise.all(Array.from({ length: Math.min(CONCURRENCY, nodes.length) }, () => worker()))
    toast.success('批量测速完成')
  } catch {
    // ignore
  } finally {
    batchTesting.value = false
  }
}

function delayColor(delay) {
  if (delay === null || delay === undefined) return 'text-muted-foreground/60'
  if (delay === 0) return 'text-red-400'
  if (delay < 200) return 'text-emerald-400'
  if (delay < 500) return 'text-yellow-400'
  return 'text-red-400'
}

function delayText(delay) {
  if (delay === null || delay === undefined) return '未测'
  if (delay === 0) return '超时'
  return `${delay} ms`
}

onMounted(() => {
  loadDevices()
  loadSubscriptions()
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
      <!-- 设备 + 订阅筛选栏 -->
      <Card>
        <CardContent class="pt-4">
          <div class="flex flex-wrap items-end gap-4">
            <!-- 设备选择 -->
            <div class="flex flex-col gap-1.5 min-w-[200px]">
              <label class="text-sm font-medium text-foreground flex items-center gap-1">
                <Monitor class="h-3.5 w-3.5" />
                选择设备
              </label>
              <Select v-model="selectedDeviceId">
                <SelectTrigger class="w-[220px]">
                  <SelectValue placeholder="选择要配置的设备" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="d in devices"
                    :key="d.id"
                    :value="String(d.id)"
                  >
                    {{ d.name }} ({{ d.source_ip }})
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!-- 订阅筛选 -->
            <div class="flex flex-col gap-1.5 min-w-[200px]">
              <label class="text-sm font-medium text-foreground flex items-center gap-1">
                <Globe class="h-3.5 w-3.5" />
                筛选订阅
              </label>
              <Select v-model="selectedSubId">
                <SelectTrigger class="w-[220px]">
                  <SelectValue placeholder="全部订阅" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部订阅</SelectItem>
                  <SelectItem
                    v-for="s in subscriptions"
                    :key="s.id"
                    :value="String(s.id)"
                  >
                    {{ s.name }} ({{ s.node_count }})
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!-- 当前分配信息 -->
            <div v-if="selectedDevice" class="flex items-center gap-2 ml-auto">
              <span class="text-sm text-muted-foreground">当前节点：</span>
              <Badge v-if="assignedNode" variant="success">{{ assignedNode }}</Badge>
              <Badge v-else variant="secondary">未分配</Badge>
            </div>
          </div>
          <p v-if="selectedDevice" class="mt-2 text-xs text-muted-foreground">
            点击下方节点即为设备「{{ selectedDevice.name }}」分配该节点，立即生效
          </p>
          <p v-else class="mt-2 text-xs text-muted-foreground">
            请先在上方选择设备，然后点击节点为其分配代理
          </p>
        </CardContent>
      </Card>

      <!-- 节点列表卡片 -->
      <div>
        <div class="flex items-center gap-2 mb-3">
          <h3 class="text-base font-semibold">节点列表</h3>
          <Badge variant="secondary">{{ filteredProxies.length }} 个</Badge>
        </div>
        <div v-if="loading" class="flex items-center justify-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-primary" />
        </div>
        <div v-else-if="filteredProxies.length === 0" class="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Inbox class="h-10 w-10 mb-2 opacity-50" />
          <span class="text-sm">暂无节点</span>
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          <div
            v-for="p in filteredProxies"
            :key="p.name"
            class="group relative cursor-pointer rounded-lg border p-3 transition-all hover:shadow-md"
            :class="assignedNode === p.name
              ? 'border-primary bg-primary/10 ring-1 ring-primary/30'
              : 'border-border hover:border-primary/50'"
            @click="onAssignNode(p.name)"
          >
            <!-- 选中标记 -->
            <div class="absolute -right-1.5 -top-1.5">
              <div
                v-if="assignedNode === p.name"
                class="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground shadow"
              >
                <Check class="h-3 w-3" />
              </div>
            </div>

            <!-- 卡片内容 -->
            <div class="space-y-2">
              <!-- 节点名称 -->
              <div class="flex items-center gap-1.5">
                <component
                  :is="p.alive ? Wifi : WifiOff"
                  class="h-3.5 w-3.5 shrink-0"
                  :class="p.alive ? 'text-emerald-400' : 'text-muted-foreground'"
                />
                <span
                  class="text-sm font-medium truncate flex-1"
                  :class="assignedNode === p.name ? 'text-primary' : 'text-foreground'"
                  :title="p.name"
                >
                  {{ p.name }}
                </span>
              </div>

              <!-- 订阅来源 -->
              <div class="flex items-center gap-1.5">
                <Globe class="h-3 w-3 text-muted-foreground shrink-0" />
                <span v-if="nodeSource[p.name]" class="text-xs text-muted-foreground truncate">{{ nodeSource[p.name] }}</span>
                <span v-else class="text-xs text-muted-foreground">未知来源</span>
              </div>

              <!-- 底部信息：类型 + 延迟 -->
              <div class="flex items-center justify-between pt-1 border-t border-border/50">
                <Badge variant="outline" class="text-[10px] h-5">{{ p.type }}</Badge>
                <div class="flex items-center gap-1.5">
                  <button
                    type="button"
                    class="rounded p-0.5 text-muted-foreground transition-colors hover:text-primary disabled:opacity-50"
                    :disabled="testingMap[p.name]"
                    @click.stop="onTestDelay(p.name)"
                  >
                    <Loader2 v-if="testingMap[p.name]" class="h-3.5 w-3.5 animate-spin" />
                    <Zap v-else class="h-3.5 w-3.5" />
                  </button>
                  <span class="text-xs font-medium" :class="delayColor(delayMap[p.name])">
                    {{ delayText(delayMap[p.name]) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
