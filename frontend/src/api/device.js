import client from './client'

export async function listDevices() {
  const resp = await client.get('/api/devices')
  return resp.data
}

export async function createDevice(data) {
  const resp = await client.post('/api/devices', data)
  return resp.data
}

export async function updateDevice(id, data) {
  const resp = await client.put(`/api/devices/${id}`, data)
  return resp.data
}

export async function deleteDevice(id) {
  const resp = await client.delete(`/api/devices/${id}`)
  return resp.data
}

export async function discoverClients() {
  const resp = await client.get('/api/devices/discover')
  return resp.data
}
