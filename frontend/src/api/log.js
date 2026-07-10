import client from './client'

export async function getAllLogs(params = {}) {
  const resp = await client.get('/api/logs', { params })
  return resp.data
}

export async function getAppLogs(params = {}) {
  const resp = await client.get('/api/logs/app', { params })
  return resp.data
}

export async function getMihomoLogs(params = {}) {
  const resp = await client.get('/api/logs/mihomo', { params })
  return resp.data
}
