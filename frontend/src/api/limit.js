import client from './client'

export async function listLimits() {
  const resp = await client.get('/api/limits')
  return resp.data
}

export async function createLimit(payload) {
  const resp = await client.post('/api/limits', payload)
  return resp.data
}

export async function updateLimit(id, payload) {
  const resp = await client.put(`/api/limits/${id}`, payload)
  return resp.data
}

export async function deleteLimit(id) {
  const resp = await client.delete(`/api/limits/${id}`)
  return resp.data
}
