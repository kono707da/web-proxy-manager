<script setup>
import { ref, reactive, onMounted } from 'vue'
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
  RotateCw,
  Inbox
} from 'lucide-vue-next'
import { formatDateTime } from '@/lib/format'
import {
  listSubscriptions,
  createSubscription,
  updateSubscription,
  deleteSubscription,
  updateSubscriptionNow,
  updateAllSubscriptions
} from '@/api/subscription'

const toast = useToast()
const { confirm } = useConfirm()

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)
const updatingId = ref(null) // 当前正在立即更新的订阅 id
const updatingAll = ref(false) // 是否正在批量更新
const togglingId = ref(null) // 当前正在切换开关的订阅 id
const useProxyUpdate = ref(false) // 更新时是否通过当前选中节点代理
const customProxyUrl = ref('') // 自定义代理 URL（用于订阅更新）

const form = reactive({
  name: '',
  url: '',
  enabled: true,
  auto_update: false,
  update_interval: 3600
})

// 加载订阅列表
async function loadList() {
  loading.value = true
  try {
    const data = await listSubscriptions()
    list.value = Array.isArray(data) ? data : data.items || []
  } catch (e) {
    toast.error('获取订阅列表失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.url = ''
  form.enabled = true
  form.auto_update = false
  form.update_interval = 3600
  dialogVisible.value = true
}

function openEdit(row) {
  editing.value = row
  form.name = row.name || ''
  form.url = row.url || ''
  form.enabled = !!row.enabled
  form.auto_update = !!row.auto_update
  form.update_interval = row.update_interval ?? 3600
  dialogVisible.value = true
}

async function onSave() {
  if (!form.name) {
    toast.warning('请输入订阅名称')
    return
  }
  if (!form.url) {
    toast.warning('请输入订阅 URL')
    return
  }
  try {
    const payload = {
      name: form.name,
      url: form.url,
      enabled: form.enabled,
      auto_update: form.auto_update,
      update_interval: Number(form.update_interval) || 0
    }
    if (editing.value) {
      await updateSubscription(editing.value.id, payload)
      toast.success('订阅已更新')
    } else {
      await createSubscription(payload)
      toast.success('订阅已创建')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e) {
    toast.error('保存订阅失败', e.response?.data?.detail || e.message)
  }
}

async function onDelete(row) {
  const ok = await confirm(`确定删除订阅「${row.name}」？`, {
    title: '删除订阅',
    type: 'danger'
  })
  if (!ok) return
  try {
    await deleteSubscription(row.id)
    toast.success('订阅已删除')
    await loadList()
  } catch (e) {
    toast.error('删除订阅失败', e.response?.data?.detail || e.message)
  }
}

// 立即更新单个订阅
async function onUpdateNow(row) {
  updatingId.value = row.id
  try {
    const proxy = customProxyUrl.value.trim()
    await updateSubscriptionNow(row.id, useProxyUpdate.value, proxy)
    toast.success(`订阅「${row.name}」更新成功${useProxyUpdate.value || proxy ? '（代理）' : ''}`)
    await loadList()
  } catch (e) {
    toast.error(`订阅「${row.name}」更新失败`, e.response?.data?.detail || e.message)
  } finally {
    updatingId.value = null
  }
}

// 更新全部订阅
async function onUpdateAll() {
  updatingAll.value = true
  try {
    const proxy = customProxyUrl.value.trim()
    await updateAllSubscriptions(useProxyUpdate.value, proxy)
    toast.success(`全部订阅更新完成${useProxyUpdate.value || proxy ? '（代理）' : ''}`)
    await loadList()
  } catch (e) {
    toast.error('批量更新订阅失败', e.response?.data?.detail || e.message)
  } finally {
    updatingAll.value = false
  }
}

// 切换启用状态
async function onToggleEnabled(row, newValue) {
  togglingId.value = row.id
  try {
    await updateSubscription(row.id, { enabled: newValue })
    toast.success(newValue ? '已启用' : '已禁用')
  } catch (e) {
    toast.error('切换启用状态失败', e.response?.data?.detail || e.message)
  } finally {
    togglingId.value = null
    await loadList()
  }
}

// 切换自动更新
async function onToggleAutoUpdate(row, newValue) {
  togglingId.value = row.id
  try {
    await updateSubscription(row.id, { auto_update: newValue })
    toast.success(newValue ? '已开启自动更新' : '已关闭自动更新')
  } catch (e) {
    toast.error('切换自动更新失败', e.response?.data?.detail || e.message)
  } finally {
    togglingId.value = null
    await loadList()
  }
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">订阅管理</h2>
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2 rounded-md border border-border px-3 py-1.5">
          <Switch
            id="use-proxy-update"
            :checked="useProxyUpdate"
            @update:checked="(v) => (useProxyUpdate = v)"
          />
          <Label for="use-proxy-update" class="cursor-pointer text-sm">
            走内核代理
          </Label>
        </div>
        <Input
          v-model="customProxyUrl"
          placeholder="自定义代理 http://ip:port"
          class="w-52 h-8 text-sm"
        />
        <div class="flex gap-2">
          <Button variant="secondary" :disabled="loading" @click="loadList">
            <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
            <RefreshCw v-else class="h-4 w-4" />
            刷新
          </Button>
          <Button variant="secondary" :disabled="updatingAll" @click="onUpdateAll">
            <Loader2 v-if="updatingAll" class="h-4 w-4 animate-spin" />
            <RotateCw v-else class="h-4 w-4" />
            更新全部
          </Button>
          <Button @click="openCreate">
            <Plus class="h-4 w-4" />
            新增订阅
          </Button>
        </div>
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
                <TableHead class="min-w-[200px]">URL</TableHead>
                <TableHead class="w-20">节点数</TableHead>
                <TableHead class="w-24">自动更新</TableHead>
                <TableHead class="w-20">启用</TableHead>
                <TableHead class="min-w-[160px]">最后更新</TableHead>
                <TableHead class="w-20">状态</TableHead>
                <TableHead class="w-52 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, i) in list" :key="row.id">
                <TableCell class="text-muted-foreground">{{ i + 1 }}</TableCell>
                <TableCell class="font-medium text-foreground">
                  <div class="flex items-center gap-2">
                    {{ row.name }}
                    <Badge v-if="row.enabled" variant="success">生效中</Badge>
                  </div>
                </TableCell>
                <TableCell class="text-muted-foreground">
                  <span class="block max-w-[260px] truncate" :title="row.url">{{ row.url || '—' }}</span>
                </TableCell>
                <TableCell class="text-muted-foreground">{{ row.node_count ?? 0 }}</TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    :disabled="togglingId === row.id"
                    class="px-2"
                    @click="onToggleAutoUpdate(row, !row.auto_update)"
                  >
                    <Loader2 v-if="togglingId === row.id" class="h-3.5 w-3.5 animate-spin" />
                    <Badge v-else :variant="row.auto_update ? 'success' : 'secondary'" class="text-xs">
                      {{ row.auto_update ? '开' : '关' }}
                    </Badge>
                  </Button>
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    :disabled="togglingId === row.id"
                    class="px-2"
                    @click="onToggleEnabled(row, !row.enabled)"
                  >
                    <Loader2 v-if="togglingId === row.id" class="h-3.5 w-3.5 animate-spin" />
                    <Badge v-else :variant="row.enabled ? 'success' : 'secondary'" class="text-xs">
                      {{ row.enabled ? '开' : '关' }}
                    </Badge>
                  </Button>
                </TableCell>
                <TableCell class="text-muted-foreground">{{ formatDateTime(row.last_update) }}</TableCell>
                <TableCell>
                  <Badge v-if="row.last_error" variant="destructive">错误</Badge>
                  <Badge v-else variant="success">正常</Badge>
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
                      :disabled="updatingId === row.id"
                      @click="onUpdateNow(row)"
                    >
                      <Loader2 v-if="updatingId === row.id" class="h-3.5 w-3.5 animate-spin" />
                      <RotateCw v-else class="h-3.5 w-3.5" />
                      更新
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
                <TableCell colspan="9">
                  <div class="flex flex-col items-center justify-center py-10 text-muted-foreground">
                    <Inbox class="h-10 w-10 mb-2 opacity-50" />
                    <span class="text-sm">暂无订阅</span>
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

    <!-- 新建/编辑订阅对话框 -->
    <Dialog :open="dialogVisible" @update:open="(v) => (dialogVisible = v)">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ editing ? '编辑订阅' : '新增订阅' }}</DialogTitle>
          <DialogDescription>
            {{ editing ? '修改订阅信息' : '添加一个新的订阅地址' }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4">
          <div class="space-y-2">
            <Label for="sub-name">名称</Label>
            <Input id="sub-name" v-model="form.name" placeholder="请输入订阅名称" />
          </div>
          <div class="space-y-2">
            <Label for="sub-url">订阅 URL</Label>
            <Input id="sub-url" v-model="form.url" placeholder="https://example.com/sub.yaml" />
          </div>
          <div class="space-y-2">
            <Label for="sub-interval">更新间隔（秒）</Label>
            <Input id="sub-interval" type="number" v-model="form.update_interval" placeholder="3600" />
            <p class="text-xs text-muted-foreground">自动更新开启后按此间隔拉取，单位秒</p>
          </div>
          <div class="flex items-center justify-between rounded-md border border-border p-3">
            <div class="flex flex-col gap-0.5">
              <Label for="sub-auto" class="cursor-pointer">自动更新</Label>
              <span class="text-xs text-muted-foreground">按设定间隔自动拉取订阅</span>
            </div>
            <Switch id="sub-auto" v-model:checked="form.auto_update" />
          </div>
          <div class="flex items-center justify-between rounded-md border border-border p-3">
            <div class="flex flex-col gap-0.5">
              <Label for="sub-enabled" class="cursor-pointer">启用</Label>
              <span class="text-xs text-muted-foreground">关闭后该订阅不会被加载</span>
            </div>
            <Switch id="sub-enabled" v-model:checked="form.enabled" />
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
