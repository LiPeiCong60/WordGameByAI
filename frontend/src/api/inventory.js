import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export const listInventory = (gameId) => apiGet(`/games/${gameId}/inventory`)
export const createInventoryRecord = (gameId, data) => apiPost(`/games/${gameId}/inventory`, data)
export const updateInventoryRecord = (id, data) => apiPatch(`/inventory/${id}`, data)
export const deleteInventoryRecord = (id) => apiDelete(`/inventory/${id}`)
export const transferItem = (data) => apiPost('/inventory/transfer', data)
export const useItem = (data) => apiPost('/inventory/use', data)
export const equipItem = (data) => apiPost('/inventory/equip', data)
export const unequipItem = (data) => apiPost('/inventory/unequip', data)
