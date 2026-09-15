const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options)
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with status ${response.status}`)
  }
  return data
}

export async function checkHealth() {
  return request('/api/health')
}

export async function listChannels() {
  return request('/api/channels')
}

export async function createChannel(channel) {
  return request('/api/channels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel }),
  })
}

export async function updateChannel(id, updates) {
  return request(`/api/channels/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
}

export async function deleteChannel(id) {
  return request(`/api/channels/${id}`, { method: 'DELETE' })
}

export async function validateChannel(id) {
  return request(`/api/channels/${id}/validate`, { method: 'POST' })
}

export async function fetchTelegramMessages(date) {
  return request('/api/telegram/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(date ? { date } : {}),
  })
}
