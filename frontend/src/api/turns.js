import { API_BASE_URL, apiDelete, apiPost } from './http'

export const runTurn = (gameId, userInput) => apiPost(`/games/${gameId}/turn`, { user_input: userInput })
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

export async function runTurnStream(gameId, userInput, onEvent) {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/turn/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_input: userInput })
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
