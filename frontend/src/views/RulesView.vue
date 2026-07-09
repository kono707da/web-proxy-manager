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
import {
  listRules,
  createRule,
  updateRule,
  deleteRule
} from '@/api/rule'

const toast = useToast()
const { confirm } = useConfirm()

// 规则类型与目标策略组可选项
const RULE_TYPES = ['DOMAIN-SUFFIX', 'DOMAIN', 'DOMAIN-KEYWORD', 'IP-CIDR', 'GEOIP', 'PROCESS-NAME', 'MATCH']
const TARGETS = ['PROXY', 'DIRECT', 'REJECT']

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)

const form = reactive({
  name: '',
  rule_type: 'DOMAIN-SUFFIX',
  value: '',
  target: 'PROXY',
  enabled: true,
  priority: 0
})

// 加载规则列表
async function loadList() {
  loading.value = true
  try {
    const data = await listRules()
    list.value = Array.isArray(data) ? data : data.items || []
  } catch (e) {
    toast.error('获取规则列表失败', e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.rule_type = 'DOMAIN-SUFFIX'
  form.value = ''
  form.target = 'PROXY'
  form.enabled = true
  form.priority = 0
  dialogVisible.value = true
}

function openEdit(row) {
  editing.value = row
  form.name = row.name || ''
  form.rule_type = row.rule_type || 'DOMAIN-SUFFIX'
  form.value = row.value || ''
  form.target = row.target || 'PROXY'
  form.enabled = !!row.enabled
  form.priority = row.priority ?? 0
  dialogVisible.value = true
}

async function onSave() {
  if (!form.name) {
    toast.warning('请输入规则名称')
    return
  }
  if (!form.value) {
    toast.warning('请输入匹配值')
    return
  }
  try {
    const payload = {
      name: form.name,
      rule_type: form.rule_type,
      value: form.value,
      target: form.target,
      enabled: form.enabled,
      priority: Number(form.priority) || 0
    }
    if (editing.value) {
      await updateRule(editing.value.id, payload)
      toast.success('规则已更新')
    } else {
      await createRule(payload)
      toast.success('规则已创建')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e) {
    toast.error('保存规则失败', e.response?.data?.detail || e.message)
  }
}

async function onDelete(row) {
  const ok = await confirm(`确定删除规则「${row.name}」？`, {
    title: '删除规则',
    type: 'danger'
  })
  if (!ok) return
  try {
    await deleteRule(row.id)
    toast.success('规则已删除')
    await loadList()
  } catch (e) {
    toast.error('删除规则失败', e.response?.data?.detail || e.message)
  }
}

// 切换启用状态（失败回滚）
async function onToggleEnabled(row, newValue) {
  const old = !!row.enabled
  row.enabled = newValue
  try {
    await updateRule(row.id, { enabled: newValue })
    toast.success(newValue ? '已启用' : '已禁用')
  } catch (e) {
    row.enabled = old
    toast.error('切换启用状态失败', e.response?.data?.detail || e.message)
  }
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold tracking-tight">规则路由</h2>
      <div class="flex gap-2">
        <Button variant="secondary" :disabled="loading" @click="loadList">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <RefreshCw v-else class="h-4 w-4" />
          刷新
        </Button>
        <Button @click="openCreate">
          <Plus class="h-4 w-4" />
          新增规则
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
                <TableHead class="w-36">类型</TableHead>
                <TableHead class="min-w-[180px]">匹配值</TableHead>
                <TableHead class="w-28">目标策略组</TableHead>
                <TableHead class="w-20">优先级</TableHead>
                <TableHead class="w-20">启用</TableHead>
                <TableHead class="w-32 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, i) in list" :key="row.id">
                <TableCell class="text-muted-foreground">{{ i + 1 }}</TableCell>
                <TableCell class="font-medium text-foreground">{{ row.name }}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{{ row.rule_type }}</Badge>
                </TableCell>
                <TableCell class="text-muted-foreground">
                  <span class="block max-w-[260px] truncate" :title="row.value">{{ row.value || '—' }}</span>
                </TableCell>
                <TableCell>
                  <Badge>{{ row.target }}</Badge>
                </TableCell>
                <TableCell class="text-muted-foreground">{{ row.priority ?? 0 }}</TableCell>
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
                    <span class="text-sm">暂无规则</span>
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

    <!-- 新建/编辑规则对话框 -->
    <Dialog :open="dialogVisible" @update:open="(v) => (dialogVisible = v)">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ editing ? '编辑规则' : '新增规则' }}</DialogTitle>
          <DialogDescription>
            {{ editing ? '修改路由规则' : '添加一条新的路由规则' }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4">
          <div class="space-y-2">
            <Label for="rule-name">名称</Label>
            <Input id="rule-name" v-model="form.name" placeholder="请输入规则名称" />
          </div>
          <div class="space-y-2">
            <Label for="rule-type">规则类型</Label>
            <Select v-model="form.rule_type">
              <SelectTrigger id="rule-type">
                <SelectValue placeholder="请选择规则类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="t in RULE_TYPES" :key="t" :value="t">{{ t }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label for="rule-value">匹配值</Label>
            <Input id="rule-value" v-model="form.value" placeholder="如 example.com 或 192.168.0.0/16" />
          </div>
          <div class="space-y-2">
            <Label for="rule-target">目标策略组</Label>
            <Select v-model="form.target">
              <SelectTrigger id="rule-target">
                <SelectValue placeholder="请选择目标" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="t in TARGETS" :key="t" :value="t">{{ t }}</SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">选择 PROXY/DIRECT/REJECT，或在下方输入自定义策略组名</p>
          </div>
          <div class="space-y-2">
            <Label for="rule-target-custom">自定义目标（可选）</Label>
            <Input
              id="rule-target-custom"
              v-model="form.target"
              placeholder="留空则使用上方选择的目标，可输入自定义策略组名"
            />
          </div>
          <div class="space-y-2">
            <Label for="rule-priority">优先级</Label>
            <Input id="rule-priority" type="number" v-model="form.priority" placeholder="0" />
            <p class="text-xs text-muted-foreground">数字越大优先级越高</p>
          </div>
          <div class="flex items-center justify-between rounded-md border border-border p-3">
            <div class="flex flex-col gap-0.5">
              <Label for="rule-enabled" class="cursor-pointer">启用</Label>
              <span class="text-xs text-muted-foreground">关闭后该规则不生效</span>
            </div>
            <Switch id="rule-enabled" v-model:checked="form.enabled" />
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
