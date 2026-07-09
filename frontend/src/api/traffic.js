import client from './client'

export async function getRealtimeTraffic() {
  const resp = await client.get('/api/traffic/realtime')
  return resp.data
}

export async function getMemoryUsage() {
  const resp = await client.get('/api/traffic/memory')
  return resp.data
}

export async function listTrafficStats() {
  const resp = await client.get('/api/traffic/stats')
  return resp.data
}

export async function resetTrafficStats() {
  const resp = await client.delete('/api/traffic/stats')
  return resp.data
}
