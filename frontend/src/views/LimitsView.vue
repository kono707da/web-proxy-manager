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
  Inbox
} from 'lucide-vue-next'
import { formatSpeed } from '@/lib/format'
import {
  listLimits,
  createLimit,
  updateLimit,
  deleteLimit
} from '@/api/limit'

const toast = useToast()
const { confirm } = useConfirm()

// 限速范围可选项
const SCOPE_OPTIONS = [
  { value: 'global', label: '全局' },
  { value: 'group', label: '策略组' },
  { value: 'client', label: '客户端 IP' }
]

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)

const form = reactive({
  name: '',
  scope: 'global',
  target: '',
  download_limit: 0,
  upload_limit: 0,
  enabled: true
})

// 表单中下载/上传限速预览
const dlPreview = computed(() => formatSpeed(Number(form.download_limit) || 0))
const ulPreview = computed(() => formatSpeed(Number(form.upload_limit) || 0))

// 加载限速列表
async function loadList() {
  loading.value = true
  try {
    const data = await listLimits()
    list.value = Array.isArray(data) ? data : data.items || []
  } catch (e) {
    toast.error('获取限速列表失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.scope = 'global'
  form.target = ''
  form.download_limit = 0
  form.upload_limit = 0
  form.enabled = true
  dialogVisible.value = true
}

function openEdit(row) {
  editing.value = row
  form.name = row.name || ''
  form.scope = row.scope || 'global'
  form.target = row.target || ''
  form.download_limit = row.download_limit ?? 0
  form.upload_limit = row.upload_limit ?? 0
  form.enabled = !!row.enabled
  dialogVisible.value = true
}

async function onSave() {
  if (!form.name) {
    toast.warning('请输入限速名称')
    return
  }
  if (form.scope !== 'global' && !form.target) {
    toast.warning('请输入限速目标')
    return
  }
  try {
    const payload = {
      name: form.name,
      scope: form.scope,
      target: form.scope === 'global' ? '' : form.target,
      download_limit: Number(form.download_limit) || 0,
      upload_limit: Number(form.upload_limit) || 0,
      enabled: form.enabled
    }
    if (editing.value) {
      await updateLimit(editing.value.id, payload)
      toast.success('限速规则已更新')
    } else {
      await createLimit(payload)
      toast.success('限速规则已创建')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e) {
    toast.error('保存限速规则失败', e.response?.data?.detail || e.message)
  }
}

async function onDelete(row) {
  const ok = await confirm(`确定删除限速规则「${row.name}」？`, {
    title: '删除限速规则',
    type: 'danger'
  })
  if (!ok) return
  try {
    await deleteLimit(row.id)
    toast.success('限速规则已删除')
    await loadList()
  } catch (e) {
    toast.error('删除限速规则失败', e.response?.data?.detail || e.message)
  }
}

// 切换启用状态（失败回滚）
async function onToggleEnabled(row, newValue) {
  const old = !!row.enabled
  row.enabled = newValue
  try {
    await updateLimit(row.id, { enabled: newValue })
    toast.success(newValue ? '已启用' : '已禁用')
  } catch (e) {
    row.enabled = old
    toast.error('切换启用状态失败', e.response?.data?.detail || e.message)
  }
}

function scopeLabel(scope) {
  return SCOPE_OPTIONS.find((s) => s.value === scope)?.label || scope
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">限速控制</h2>
      <div class="flex gap-2">
        <Button variant="secondary" :disabled="loading" @click="loadList">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <RefreshCw v-else class="h-4 w-4" />
          刷新
        </Button>
        <Button @click="openCreate">
          <Plus class="h-4 w-4" />
          新增限速
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
                <TableHead class="min-w-[140px]">名称</TableHead>
                <TableHead class="w-28">范围</TableHead>
                <TableHead class="min-w-[140px]">目标</TableHead>
                <TableHead class="w-28">下载限速</TableHead>
                <TableHead class="w-28">上传限速</TableHead>
                <TableHead class="w-20">启用</TableHead>
                <TableHead class="w-32 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, i) in list" :key="row.id">
                <TableCell class="text-muted-foreground">{{ i + 1 }}</TableCell>
                <TableCell class="font-medium text-foreground">{{ row.name }}</TableCell>
                <TableCell>
                  <Badge :variant="row.scope === 'global' ? 'default' : 'secondary'">
                    {{ scopeLabel(row.scope) }}
                  </Badge>
                </TableCell>
                <TableCell class="text-muted-foreground">{{ row.scope === 'global' ? '—' : (row.target || '—') }}</TableCell>
                <TableCell class="text-muted-foreground">{{ formatSpeed(row.download_limit) }}</TableCell>
                <TableCell class="text-muted-foreground">{{ formatSpeed(row.upload_limit) }}</TableCell>
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
                <TableCell colspan="8">
                  <div class="flex flex-col items-center justify-center py-10 text-muted-foreground">
                    <Inbox class="h-10 w-10 mb-2 opacity-50" />
                    <span class="text-sm">暂无限速规则</span>
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

    <!-- 新建/编辑限速对话框 -->
    <Dialog :open="dialogVisible" @update:open="(v) => (dialogVisible = v)">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ editing ? '编辑限速规则' : '新增限速规则' }}</DialogTitle>
          <DialogDescription>
            {{ editing ? '修改限速规则' : '添加一条新的限速规则' }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4">
          <div class="space-y-2">
            <Label for="limit-name">名称</Label>
            <Input id="limit-name" v-model="form.name" placeholder="请输入限速名称" />
          </div>
          <div class="space-y-2">
            <Label for="limit-scope">范围</Label>
            <Select v-model="form.scope">
              <SelectTrigger id="limit-scope">
                <SelectValue placeholder="请选择范围" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="s in SCOPE_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label for="limit-target">目标</Label>
            <Input
              id="limit-target"
              v-model="form.target"
              :disabled="form.scope === 'global'"
              :placeholder="form.scope === 'global' ? '全局范围无需填写' : '请输入策略组名或客户端 IP'"
            />
          </div>
          <div class="space-y-2">
            <Label for="limit-dl">下载限速（B/s）</Label>
            <Input id="limit-dl" type="number" v-model="form.download_limit" placeholder="0 表示不限" />
            <p class="text-xs text-muted-foreground">单位 B/s，0 = 不限速。预览：{{ dlPreview }}</p>
          </div>
          <div class="space-y-2">
            <Label for="limit-ul">上传限速（B/s）</Label>
            <Input id="limit-ul" type="number" v-model="form.upload_limit" placeholder="0 表示不限" />
            <p class="text-xs text-muted-foreground">单位 B/s，0 = 不限速。预览：{{ ulPreview }}</p>
          </div>
          <div class="flex items-center justify-between rounded-md border border-border p-3">
            <div class="flex flex-col gap-0.5">
              <Label for="limit-enabled" class="cursor-pointer">启用</Label>
              <span class="text-xs text-muted-foreground">关闭后该限速规则不生效</span>
            </div>
            <Switch id="limit-enabled" v-model:checked="form.enabled" />
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
