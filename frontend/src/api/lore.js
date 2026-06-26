import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export const listLore = (gameId) => apiGet(`/games/${gameId}/lore`)
export const createLore = (gameId, data) => apiPost(`/games/${gameId}/lore`, data)
export const updateLore = (id, data) => apiPatch(`/lore/${id}`, data)
export const deleteLore = (id) => apiDelete(`/lore/${id}`)
export const organizeLore = (gameId, text) => apiPost(`/games/${gameId}/lore/organize`, { text })
