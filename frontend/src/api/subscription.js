import client from './client'

export async function listSubscriptions() {
  const resp = await client.get('/api/subscriptions')
  return resp.data
}

export async function createSubscription(payload) {
  const resp = await client.post('/api/subscriptions', payload)
  return resp.data
}

export async function updateSubscription(id, payload) {
  const resp = await client.put(`/api/subscriptions/${id}`, payload)
  return resp.data
}

export async function deleteSubscription(id) {
  const resp = await client.delete(`/api/subscriptions/${id}`)
  return resp.data
}

export async function updateSubscriptionNow(id, useProxy = false, customProxy = '') {
  const params = { use_proxy: useProxy }
  if (customProxy) params.custom_proxy = customProxy
  const resp = await client.post(`/api/subscriptions/${id}/update`, {}, {
    params,
    timeout: 60000
  })
  return resp.data
}

export async function updateAllSubscriptions(useProxy = false, customProxy = '') {
  const params = { use_proxy: useProxy }
  if (customProxy) params.custom_proxy = customProxy
  const resp = await client.post('/api/subscriptions/update-all', {}, {
    params,
    timeout: 120000
  })
  return resp.data
}
