import client from './client'

export async function listQuotas() {
  const resp = await client.get('/api/quotas')
  return resp.data
}

export async function createQuota(payload) {
  const resp = await client.post('/api/quotas', payload)
  return resp.data
}

export async function updateQuota(id, payload) {
  const resp = await client.put(`/api/quotas/${id}`, payload)
  return resp.data
}

export async function deleteQuota(id) {
  const resp = await client.delete(`/api/quotas/${id}`)
  return resp.data
}

export async function resetQuotaUsage(id) {
  const resp = await client.post(`/api/quotas/${id}/reset`)
  return resp.data
}
