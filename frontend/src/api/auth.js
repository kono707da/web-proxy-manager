import client from './client'

export async function login(username, password) {
  const resp = await client.post('/api/auth/login', { username, password })
  return resp.data
}

export async function getMe() {
  const resp = await client.get('/api/auth/me')
  return resp.data
}

export async function refreshToken() {
  const resp = await client.post('/api/auth/refresh')
  return resp.data
}
