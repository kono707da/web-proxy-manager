import client from './client'

export async function getStatus() {
  const resp = await client.get('/api/system/status')
  return resp.data
}

export async function getInfo() {
  const resp = await client.get('/api/system/info')
  return resp.data
}

export async function startCore() {
  const resp = await client.post('/api/system/start')
  return resp.data
}

export async function stopCore() {
  const resp = await client.post('/api/system/stop')
  return resp.data
}

export async function restartCore() {
  const resp = await client.post('/api/system/restart')
  return resp.data
}

export async function reloadCore() {
  const resp = await client.post('/api/system/reload')
  return resp.data
}

export async function updateMode(mode) {
  const resp = await client.patch('/api/system/mode', { mode })
  return resp.data
}

export async function updateLogLevel(level) {
  const resp = await client.patch('/api/system/log-level', { level })
  return resp.data
}
