import { API_BASE_URL, apiDelete, apiPost } from './http'

function buildTurnPayload(input, options = {}) {
  const base = typeof input === 'object' && input !== null ? input : { user_input: input }
  return { ...base, ...options }
}

export const runTurn = (gameId, input, options = {}) => apiPost(`/games/${gameId}/turn`, buildTurnPayload(input, options))
export const runOpening = (gameId) => apiPost(`/games/${gameId}/opening`)
export const deleteTurnsFrom = (turnId) => apiDelete(`/turns/${turnId}/from-here`)
export const regenerateTurn = (turnId) => apiPost(`/turns/${turnId}/regenerate`)

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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildTurnPayload(input, options))
  })
  return consumeNdjsonStream(response, onEvent)
}

export async function runOpeningStream(gameId, onEvent) {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/opening/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  return consumeNdjsonStream(response, onEvent)
}

export async function regenerateTurnStream(turnId, onEvent) {
  const response = await fetch(`${API_BASE_URL}/turns/${turnId}/regenerate/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  return consumeNdjsonStream(response, onEvent)
}
