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

export async function checkTelegramHealth() {
  return request('/api/health/telegram')
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

export async function fetchTelegramMessages(date, resolveUrls = false, saveJobs = false) {
  return request('/api/telegram/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...(date ? { date } : {}),
      resolve_urls: resolveUrls,
      save_jobs: saveJobs,
    }),
  })
}

export async function resolveUrl(url) {
  return request('/api/resolve-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
}

export async function listJobs(filters = {}) {
  const params = new URLSearchParams()
  if (filters.date) params.set('date', filters.date)
  if (filters.company) params.set('company', filters.company)
  if (filters.location) params.set('location', filters.location)
  const query = params.toString()
  return request(`/api/jobs${query ? `?${query}` : ''}`)
}

export async function getJob(id) {
  return request(`/api/jobs/${id}`)
}

export async function getFetchStatus() {
  return request('/api/telegram/fetch/status')
}

export async function listFetchRuns(limit = 20) {
  return request(`/api/fetch-runs?limit=${limit}`)
}
