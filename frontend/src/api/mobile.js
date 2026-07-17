import { apiGet } from './http'

export const getGameBootstrap = (gameId, turnLimit = 20) =>
  apiGet(`/v1/games/${gameId}/bootstrap`, { params: { turn_limit: turnLimit } })

export const listGameTurns = (gameId, options = {}) =>
  apiGet(`/v1/games/${gameId}/turns`, {
    params: { limit: options.limit || 20, before_id: options.before_id || undefined }
  })

export const getGameStateSync = (gameId) => apiGet(`/v1/games/${gameId}/state-sync`)
