import client from './client'

export async function listRules() {
  const resp = await client.get('/api/rules')
  return resp.data
}

export async function createRule(payload) {
  const resp = await client.post('/api/rules', payload)
  return resp.data
}

export async function updateRule(id, payload) {
  const resp = await client.put(`/api/rules/${id}`, payload)
  return resp.data
}

export async function deleteRule(id) {
  const resp = await client.delete(`/api/rules/${id}`)
  return resp.data
}
