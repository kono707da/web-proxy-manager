<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { useConfirm } from '@/composables/use-confirm'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
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
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from '@/components/ui/select'
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
  RotateCcw,
  Inbox
} from 'lucide-vue-next'
import { formatBytes } from '@/lib/format'
import {
  listQuotas,
  createQuota,
  updateQuota,
  deleteQuota,
  resetQuotaUsage
} from '@/api/quota'

const toast = useToast()
const { confirm } = useConfirm()

// 范围与周期可选项
const SCOPE_OPTIONS = [
  { value: 'client', label: '客户端 IP' },
  { value: 'group', label: '策略组' }
]
const PERIOD_OPTIONS = [
  { value: 'total', label: '总计' },
  { value: 'daily', label: '每日' },
  { value: 'monthly', label: '每月' }
]

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)
const resettingId = ref(null) // 当前正在重置已用流量的配额 id

const form = reactive({
  name: '',
  scope: 'client',
  target: '',
  quota_bytes: 0,
  period: 'monthly',
  reset_day: 1,
  enabled: true
})

// 表单中配额预览
const quotaPreview = computed(() => formatBytes(Number(form.quota_bytes) || 0))

// 加载配额列表
async function loadList() {
  loading.value = true
  try {
    const data = await listQuotas()
    list.value = Array.isArray(data) ? data : data.items || []
  } catch (e) {
    toast.error('获取配额列表失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.scope = 'client'
  form.target = ''
  form.quota_bytes = 0
  form.period = 'monthly'
  form.reset_day = 1
  form.enabled = true
  dialogVisible.value = true
}

function openEdit(row) {
  editing.value = row
  form.name = row.name || ''
  form.scope = row.scope || 'client'
  form.target = row.target || ''
  form.quota_bytes = row.quota_bytes ?? 0
  form.period = row.period || 'monthly'
  form.reset_day = row.reset_day ?? 1
  form.enabled = !!row.enabled
  dialogVisible.value = true
}

async function onSave() {
  if (!form.name) {
    toast.warning('请输入配额名称')
    return
  }
  if (!form.target) {
    toast.warning('请输入配额目标')
    return
  }
  if (form.period === 'monthly' && (Number(form.reset_day) < 1 || Number(form.reset_day) > 28)) {
    toast.warning('重置日期需在 1-28 之间')
    return
  }
  try {
    const payload = {
      name: form.name,
      scope: form.scope,
      target: form.target,
      quota_bytes: Number(form.quota_bytes) || 0,
      period: form.period,
      reset_day: form.period === 'monthly' ? Number(form.reset_day) || 1 : 1,
      enabled: form.enabled
    }
    if (editing.value) {
      await updateQuota(editing.value.id, payload)
      toast.success('配额已更新')
    } else {
      await createQuota(payload)
      toast.success('配额已创建')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e) {
    toast.error('保存配额失败', e.response?.data?.detail || e.message)
  }
}

async function onDelete(row) {
  const ok = await confirm(`确定删除配额「${row.name}」？`, {
    title: '删除配额',
    type: 'danger'
  })
  if (!ok) return
  try {
    await deleteQuota(row.id)
    toast.success('配额已删除')
    await loadList()
  } catch (e) {
    toast.error('删除配额失败', e.response?.data?.detail || e.message)
  }
}

// 重置已用流量
async function onReset(row) {
  const ok = await confirm(`确定重置配额「${row.name}」的已用流量？`, {
    title: '重置流量',
    type: 'warning'
  })
  if (!ok) return
  resettingId.value = row.id
  try {
    await resetQuotaUsage(row.id)
    toast.success(`配额「${row.name}」已用流量已重置`)
    await loadList()
  } catch (e) {
    toast.error('重置已用流量失败', e.response?.data?.detail || e.message)
  } finally {
    resettingId.value = null
  }
}

// 切换启用状态（失败回滚）
async function onToggleEnabled(row, newValue) {
  const old = !!row.enabled
  row.enabled = newValue
  try {
    await updateQuota(row.id, { enabled: newValue })
    toast.success(newValue ? '已启用' : '已禁用')
  } catch (e) {
    row.enabled = old
    toast.error('切换启用状态失败', e.response?.data?.detail || e.message)
  }
}

function scopeLabel(scope) {
  return SCOPE_OPTIONS.find((s) => s.value === scope)?.label || scope
}

function periodLabel(period) {
  return PERIOD_OPTIONS.find((p) => p.value === period)?.label || period
}

// 使用率百分比，限制在 0-100
function usagePercent(row) {
  if (!row.quota_bytes || row.quota_bytes <= 0) return 0
  const p = (row.used_bytes / row.quota_bytes) * 100
  return Math.min(100, Math.max(0, p))
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">流量配额</h2>
      <div class="flex gap-2">
        <Button variant="secondary" :disabled="loading" @click="loadList">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <RefreshCw v-else class="h-4 w-4" />
          刷新
        </Button>
        <Button @click="openCreate">
          <Plus class="h-4 w-4" />
          新增配额
        </Button>
      </div>
    </div>

    <Card>
      <CardContent class="pt-6">
        <div class="relative rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead class="w-12">#</TableHead>
                <TableHead class="min-w-[120px]">名称</TableHead>
                <TableHead class="w-28">范围</TableHead>
                <TableHead class="min-w-[120px]">目标</TableHead>
                <TableHead class="w-24">配额</TableHead>
                <TableHead class="w-24">已用</TableHead>
                <TableHead class="min-w-[120px]">使用率</TableHead>
                <TableHead class="w-20">周期</TableHead>
                <TableHead class="w-20">状态</TableHead>
                <TableHead class="w-20">启用</TableHead>
                <TableHead class="w-44 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, i) in list" :key="row.id">
                <TableCell class="text-muted-foreground">{{ i + 1 }}</TableCell>
                <TableCell class="font-medium text-foreground">{{ row.name }}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{{ scopeLabel(row.scope) }}</Badge>
                </TableCell>
                <TableCell class="text-muted-foreground">{{ row.target || '—' }}</TableCell>
                <TableCell class="text-muted-foreground">{{ formatBytes(row.quota_bytes) }}</TableCell>
                <TableCell class="text-muted-foreground">{{ formatBytes(row.used_bytes) }}</TableCell>
                <TableCell>
                  <div class="space-y-1">
                    <div class="h-2 w-full rounded bg-secondary">
                      <div class="h-2 rounded bg-primary" :style="{ width: usagePercent(row) + '%' }"></div>
                    </div>
                    <span class="text-xs text-muted-foreground">{{ usagePercent(row).toFixed(1) }}%</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{{ periodLabel(row.period) }}</Badge>
                </TableCell>
                <TableCell>
                  <Badge v-if="row.blocked" variant="destructive">已阻断</Badge>
                  <Badge v-else variant="success">正常</Badge>
                </TableCell>
                <TableCell>
                  <Switch
                    :checked="!!row.enabled"
                    @update:checked="(v) => onToggleEnabled(row, v)"
                  />
                </TableCell>
                <TableCell>
                  <div class="flex justify-end gap-1">
                    <Button variant="ghost" size="sm" @click="openEdit(row)">
                      <Pencil class="h-3.5 w-3.5" />
                      编辑
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      :disabled="resettingId === row.id"
                      @click="onReset(row)"
                    >
                      <Loader2 v-if="resettingId === row.id" class="h-3.5 w-3.5 animate-spin" />
                      <RotateCcw v-else class="h-3.5 w-3.5" />
                      重置
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      class="text-destructive hover:text-destructive"
                      @click="onDelete(row)"
                    >
                      <Trash2 class="h-3.5 w-3.5" />
                      删除
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
              <TableRow v-if="list.length === 0 && !loading" class="hover:bg-transparent">
                <TableCell colspan="11">
                  <div class="flex flex-col items-center justify-center py-10 text-muted-foreground">
                    <Inbox class="h-10 w-10 mb-2 opacity-50" />
                    <span class="text-sm">暂无配额</span>
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

    <!-- 新建/编辑配额对话框 -->
    <Dialog :open="dialogVisible" @update:open="(v) => (dialogVisible = v)">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ editing ? '编辑配额' : '新增配额' }}</DialogTitle>
          <DialogDescription>
            {{ editing ? '修改流量配额' : '添加一条新的流量配额' }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4">
          <div class="space-y-2">
            <Label for="quota-name">名称</Label>
            <Input id="quota-name" v-model="form.name" placeholder="请输入配额名称" />
          </div>
          <div class="space-y-2">
            <Label for="quota-scope">范围</Label>
            <Select v-model="form.scope">
              <SelectTrigger id="quota-scope">
                <SelectValue placeholder="请选择范围" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="s in SCOPE_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label for="quota-target">目标</Label>
            <Input id="quota-target" v-model="form.target" placeholder="请输入策略组名或客户端 IP" />
          </div>
          <div class="space-y-2">
            <Label for="quota-bytes">配额（B）</Label>
            <Input id="quota-bytes" type="number" v-model="form.quota_bytes" placeholder="0 表示不限" />
            <p class="text-xs text-muted-foreground">单位字节，预览：{{ quotaPreview }}</p>
          </div>
          <div class="space-y-2">
            <Label for="quota-period">周期</Label>
            <Select v-model="form.period">
              <SelectTrigger id="quota-period">
                <SelectValue placeholder="请选择周期" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="p in PERIOD_OPTIONS" :key="p.value" :value="p.value">{{ p.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label for="quota-reset-day">重置日期（每月几号）</Label>
            <Input
              id="quota-reset-day"
              type="number"
              v-model="form.reset_day"
              :disabled="form.period !== 'monthly'"
              :placeholder="form.period !== 'monthly' ? '仅每月周期可设置' : '1-28'"
            />
          </div>
          <div class="flex items-center justify-between rounded-md border border-border p-3">
            <div class="flex flex-col gap-0.5">
              <Label for="quota-enabled" class="cursor-pointer">启用</Label>
              <span class="text-xs text-muted-foreground">关闭后该配额不生效</span>
            </div>
            <Switch id="quota-enabled" v-model:checked="form.enabled" />
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="ghost" @click="dialogVisible = false">取消</Button>
          <Button variant="gold" @click="onSave">保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
