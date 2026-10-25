// Small fetch wrapper. Errors carry a readable message from the backend ("detail" or "error").

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch {
    throw new Error('Cannot reach the backend. Is it running on port 8000?')
  }
  if (res.status === 204) return null
  let body = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    const err = new Error(body?.error || body?.detail || `Request failed (HTTP ${res.status})`)
    err.body = body
    throw err
  }
  return body
}

export const api = {
  health: () => request('/api/health'),
  shots: () => request('/api/shots'),
  shot: (id) => request(`/api/shots/${id}`),
  createShot: (shot) => request('/api/shots', { method: 'POST', body: JSON.stringify(shot) }),
  deleteShot: (id) => request(`/api/shots/${id}`, { method: 'DELETE' }),
  diagnose: (id) => request(`/api/shots/${id}/diagnose`, { method: 'POST' }),
  progress: () => request('/api/progress'),
  usage: () => request('/api/usage'),
}
