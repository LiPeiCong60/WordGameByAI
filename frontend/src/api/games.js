import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export const listGames = () => apiGet('/games')
export const createGame = (data) => apiPost('/games', data)
export const getGame = (id) => apiGet(`/games/${id}`)
export const updateGame = (id, data) => apiPatch(`/games/${id}`, data)
export const deleteGame = (id) => apiDelete(`/games/${id}`)
export const exportGame = (id) => apiGet(`/games/${id}/export`)
export const importGame = (data) => apiPost('/games/import', data)
