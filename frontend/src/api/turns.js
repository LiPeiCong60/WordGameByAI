import { API_BASE_URL, apiDelete, apiPost, authHeaders } from './http'

function buildTurnPayload(input, options = {}) {
  const base = typeof input === 'object' && input !== null ? input : { user_input: input }
  return { ...base, ...options }
}

export const runTurn = (gameId, input, options = {}) => apiPost(`/games/${gameId}/turn`, buildTurnPayload(input, options))
export const runOpening = (gameId) => apiPost(`/games/${gameId}/opening`)

function turnActionQuery(options = {}) {
  const params = new URLSearchParams()
  if (options.game_id) params.set('game_id', String(options.game_id))
  if (options.turn_number) params.set('turn_number', String(options.turn_number))
  const query = params.toString()
  return query ? `?${query}` : ''
}

export const deleteTurnsFrom = (turnId, options = {}) => apiDelete(`/turns/${turnId}/from-here${turnActionQuery(options)}`)
export const regenerateTurn = (turnId, options = {}) => apiPost(`/turns/${turnId}/regenerate${turnActionQuery(options)}`)

async function consumeNdjsonStream(response, onEvent) {
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `请求失败：${response.status}`)
  }
  if (!response.body) {
    throw new Error('浏览器不支持流式响应。')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.trim()) continue
      onEvent(JSON.parse(line))
    }
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer))
}

export async function runTurnStream(gameId, input, onEvent, options = {}) {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/turn/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(buildTurnPayload(input, options))
  })
  return consumeNdjsonStream(response, onEvent)
}

export async function runOpeningStream(gameId, onEvent) {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/opening/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() }
  })
  return consumeNdjsonStream(response, onEvent)
}

export async function regenerateTurnStream(turnId, onEvent, options = {}) {
  const response = await fetch(`${API_BASE_URL}/turns/${turnId}/regenerate/stream${turnActionQuery(options)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() }
  })
  return consumeNdjsonStream(response, onEvent)
}
