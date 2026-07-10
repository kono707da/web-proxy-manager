<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { useConfirm } from '@/composables/use-confirm'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell
} from '@/components/ui/table'
import {
  Loader2,
  RefreshCw,
  Plus,
  Pencil,
  Trash2,
  Search,
  Monitor,
  Wifi,
  Inbox
} from 'lucide-vue-next'
import { formatDateTime } from '@/lib/format'
import {
  listDevices,
  createDevice,
  updateDevice,
  deleteDevice,
  discoverClients
} from '@/api/device'

const toast = useToast()
const { confirm } = useConfirm()

const loading = ref(false)
const devices = ref([])
const discovered = ref([])
const loadingDiscover = ref(false)

// 弹窗状态
const dialogOpen = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = reactive({
  name: '',
  source_ip: '',
  enabled: true
})

async function loadDevices() {
  loading.value = true
  try {
    devices.value = await listDevices()
  } catch (e) {
    toast.error('加载设备列表失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

async function loadDiscovered() {
  loadingDiscover.value = true
  try {
    discovered.value = await discoverClients()
  } catch {
    // mihomo 未运行时静默处理
  } finally {
    loadingDiscover.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.name = ''
  form.source_ip = ''
  form.enabled = true
  dialogOpen.value = true
}

function addLocalhost() {
  editingId.value = null
  form.name = '本机'
  form.source_ip = '127.0.0.1'
  form.enabled = true
  dialogOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.name = row.name
  form.source_ip = row.source_ip
  form.enabled = row.enabled
  dialogOpen.value = true
}

function quickAdd(ip) {
  editingId.value = null
  form.name = ''
  form.source_ip = ip
  form.enabled = true
  dialogOpen.value = true
}

async function onSave() {
  if (!form.name.trim()) {
    toast.error('请输入设备名称')
    return
  }
  if (!form.source_ip.trim()) {
    toast.error('请输入设备 IP')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateDevice(editingId.value, { ...form })
      toast.success('设备已更新')
    } else {
      await createDevice({ ...form })
      toast.success('设备已添加')
    }
    dialogOpen.value = false
    await loadDevices()
    await loadDiscovered()
  } catch (e) {
    toast.error('保存失败', e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}

async function onDelete(row) {
  const ok = await confirm({
    title: '删除设备',
    description: `确定删除设备「${row.name}」(${row.source_ip}) 吗？删除后该 IP 的流量将走默认代理。`
  })
  if (!ok) return
  try {
    await deleteDevice(row.id)
    toast.success('设备已删除')
    await loadDevices()
  } catch (e) {
    toast.error('删除失败', e.response?.data?.detail || e.message)
  }
}

async function onToggleEnabled(row, newValue) {
  try {
    await updateDevice(row.id, { enabled: newValue })
    toast.success(newValue ? '已启用' : '已禁用')
  } catch (e) {
    toast.error('切换失败', e.response?.data?.detail || e.message)
  } finally {
    await loadDevices()
  }
}

onMounted(() => {
  loadDevices()
  loadDiscovered()
})
</script>

<template>
  <div class="space-y-6">
    <!-- 标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">设备管理</h1>
        <p class="text-sm text-muted-foreground mt-1">
          添加设备后，到「代理节点」页面为设备选择代理节点
        </p>
      </div>
      <div class="flex gap-2">
        <Button variant="outline" size="sm" :disabled="loadingDiscover" @click="loadDiscovered">
          <RefreshCw v-if="loadingDiscover" class="h-4 w-4 animate-spin" />
          <Search v-else class="h-4 w-4" />
          扫描客户端
        </Button>
        <Button size="sm" variant="outline" @click="addLocalhost">
          <Monitor class="h-4 w-4" />
          添加本机
        </Button>
        <Button size="sm" @click="openCreate">
          <Plus class="h-4 w-4" />
          添加设备
        </Button>
      </div>
    </div>

    <!-- 使用说明 -->
    <Card>
      <CardContent class="pt-4">
        <div class="flex items-start gap-3 text-sm">
          <Monitor class="h-5 w-5 text-primary shrink-0 mt-0.5" />
          <div class="space-y-1 text-muted-foreground">
            <p><span class="text-foreground font-medium">工作原理：</span>添加设备后，到「代理节点」页面通过设备下拉框选择设备，点击节点即可为该设备分配代理节点。国内流量仍走直连，仅代理流量按设备分配。</p>
            <p><span class="text-foreground font-medium">本机设备：</span>点击「添加本机」可将服务器自身（127.0.0.1）加入设备管理，为本机流量分配固定节点。</p>
            <p><span class="text-foreground font-medium">客户端配置：</span>Windows 设置 → 代理 → 填写 <code class="text-primary">服务器IP:7890</code>；Android WiFi → 代理 → 手动 → 填写 <code class="text-primary">服务器IP:7890</code></p>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 自动发现 -->
    <Card v-if="discovered.length > 0">
      <CardHeader>
        <CardTitle class="text-base flex items-center gap-2">
          <Wifi class="h-4 w-4 text-primary" />
          发现未分配客户端
        </CardTitle>
        <CardDescription>以下 IP 当前正在使用代理但未分配设备，点击可快速添加</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="flex flex-wrap gap-2">
          <div
            v-for="c in discovered"
            :key="c.source_ip"
            class="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 cursor-pointer hover:border-primary hover:bg-primary/5 transition-colors"
            @click="quickAdd(c.source_ip)"
          >
            <span class="text-sm font-mono">{{ c.source_ip }}</span>
            <Badge variant="secondary" class="text-xs">{{ c.connections }} 连接</Badge>
            <span v-if="c.host" class="text-xs text-muted-foreground truncate max-w-[120px]">{{ c.host }}</span>
            <Plus class="h-3 w-3 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 设备列表 -->
    <Card>
      <CardHeader>
        <CardTitle class="text-base">设备列表</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="loading" class="flex items-center justify-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-primary" />
        </div>
        <div v-else-if="devices.length === 0" class="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Inbox class="h-10 w-10 mb-2" />
          <p>暂无设备，点击「添加设备」或「扫描客户端」开始</p>
        </div>
        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>设备名称</TableHead>
              <TableHead>IP 地址</TableHead>
              <TableHead>当前节点</TableHead>
              <TableHead>启用</TableHead>
              <TableHead>最后在线</TableHead>
              <TableHead class="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="row in devices" :key="row.id">
              <TableCell class="font-medium">{{ row.name }}</TableCell>
              <TableCell class="font-mono text-sm">{{ row.source_ip }}</TableCell>
              <TableCell>
                <Badge v-if="row.proxy_name" variant="secondary" class="text-xs">
                  {{ row.proxy_name }}
                </Badge>
                <span v-else class="text-xs text-muted-foreground">未分配</span>
              </TableCell>
              <TableCell>
                <Switch
                  :key="`dev-${row.id}-${row.enabled}`"
                  :checked="!!row.enabled"
                  @update:checked="(v) => onToggleEnabled(row, v)"
                />
              </TableCell>
              <TableCell class="text-sm text-muted-foreground">
                {{ formatDateTime(row.last_seen) }}
              </TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-1">
                  <Button variant="ghost" size="sm" @click="openEdit(row)">
                    <Pencil class="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="sm" @click="onDelete(row)">
                    <Trash2 class="h-3.5 w-3.5" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>

    <!-- 新增/编辑弹窗 -->
    <Dialog :open="dialogOpen" @update:open="(v) => dialogOpen = v">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑设备' : '添加设备' }}</DialogTitle>
          <DialogDescription>
            代理节点请在「代理节点」页面通过设备下拉框选择
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <Label>设备名称</Label>
            <Input v-model="form.name" placeholder="如：我的电脑、手机" />
          </div>
          <div class="space-y-2">
            <Label>设备 IP 地址</Label>
            <Input v-model="form.source_ip" placeholder="如：192.168.1.100" />
          </div>
          <div class="flex items-center gap-2">
            <Switch :checked="form.enabled" @update:checked="(v) => form.enabled = v" />
            <Label class="cursor-pointer" @click="form.enabled = !form.enabled">启用</Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="dialogOpen = false">取消</Button>
          <Button :disabled="saving" @click="onSave">
            <Loader2 v-if="saving" class="h-4 w-4 animate-spin mr-1" />
            {{ editingId ? '保存' : '添加' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
