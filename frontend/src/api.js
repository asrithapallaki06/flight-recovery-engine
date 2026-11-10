// Every call to the backend lives here, so components never build URLs themselves.

async function request(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${res.status})`
    throw new Error(detail)
  }
  return res.json()
}

export function getModelMetrics() {
  return request('/api/model')
}

export function runSimulation({ groundStopStart, groundStopEnd, reserveCrews, useRisk }) {
  return request('/api/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ground_stop_start: groundStopStart,
      ground_stop_end: groundStopEnd,
      reserve_crews: reserveCrews,
      use_risk: useRisk,
    }),
  })
}
