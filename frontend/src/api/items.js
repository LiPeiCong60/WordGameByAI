import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export const listItems = (gameId) => apiGet(`/games/${gameId}/items`)
export const createItem = (gameId, data) => apiPost(`/games/${gameId}/items`, data)
export const updateItem = (id, data) => apiPatch(`/items/${id}`, data)
export const deleteItem = (id) => apiDelete(`/items/${id}`)
