import { apiGet, apiPatch } from './http'

export const getAdminSummary = () => apiGet('/admin/summary')
export const listAdminUsers = () => apiGet('/admin/users')
export const listAdminGames = () => apiGet('/admin/games')
export const updateAdminUser = (id, data) => apiPatch(`/admin/users/${id}`, data)
