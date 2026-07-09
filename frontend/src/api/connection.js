import client from './client'

export async function listConnections() {
  const resp = await client.get('/api/connections')
  return resp.data
}

export async function closeConnection(id) {
  const resp = await client.delete(`/api/connections/${id}`)
  return resp.data
}

export async function closeAllConnections() {
  const resp = await client.delete('/api/connections')
  return resp.data
}
