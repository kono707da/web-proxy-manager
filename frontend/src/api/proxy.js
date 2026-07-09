import client from './client'

export async function listProxies() {
  const resp = await client.get('/api/proxies')
  return resp.data
}

export async function listGroups() {
  const resp = await client.get('/api/proxies/groups')
  return resp.data
}

export async function selectProxy(group, name) {
  const resp = await client.put(`/api/proxies/${group}/select`, { name })
  return resp.data
}

export async function testDelay(name) {
  const resp = await client.get(`/api/proxies/${name}/delay`, { timeout: 30000 })
  return resp.data
}
