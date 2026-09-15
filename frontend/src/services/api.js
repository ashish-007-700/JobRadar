const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`)
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }
  return response.json()
}
