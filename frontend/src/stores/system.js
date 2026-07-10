import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getStatus } from '@/api/system'
import { listGroups } from '@/api/proxy'

export const useSystemStore = defineStore('system', () => {
  // mihomo 内核状态
  const running = ref(false)
  const mode = ref('')
  const mixedPort = ref(null)
  const apiPort = ref(null)
  const version = ref('')
  const lastError = ref('')
  // 当前各代理分组选中节点 { [groupName]: nodeName }
  const groupNow = ref({})
  // PROXY 组当前选中节点（最常用的那个）
  const currentProxy = computed(() => groupNow.value['PROXY'] || '')
  // 轮询定时器
  let timer = null

  async function refresh() {
    try {
      const s = await getStatus()
      running.value = !!s.running
      mode.value = s.mode || ''
      mixedPort.value = s.mixed_port
      apiPort.value = s.api_port
      version.value = s.version || ''
      lastError.value = s.last_error || ''
    } catch {
      running.value = false
    }
    // 只有运行中才拉取分组当前节点
    if (running.value) {
      try {
        const groups = await listGroups()
        const map = {}
        ;(groups || []).forEach((g) => {
          map[g.name] = g.now || ''
        })
        groupNow.value = map
      } catch {
        // 静默
      }
    } else {
      groupNow.value = {}
    }
  }

  function startPolling(interval = 5000) {
    stopPolling()
    refresh()
    timer = setInterval(refresh, interval)
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return {
    running, mode, mixedPort, apiPort, version, lastError,
    groupNow, currentProxy,
    refresh, startPolling, stopPolling
  }
})
