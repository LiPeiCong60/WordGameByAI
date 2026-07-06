import { apiDelete, apiGet, apiPatch, apiPut } from './http'

export const getAdminSummary = () => apiGet('/admin/summary')
export const listAdminUsers = () => apiGet('/admin/users')
export const listAdminGames = () => apiGet('/admin/games')
export const updateAdminUser = (id, data) => apiPatch(`/admin/users/${id}`, data)
export const getAdminModelConfig = () => apiGet('/admin/model-config')
export const saveAdminModel = (data) => apiPut('/admin/model-config/models', data)
export const deleteAdminModel = (id) => apiDelete(`/admin/model-config/models/${id}`)
export const saveAdminModelLevel = (data) => apiPut('/admin/model-config/levels', data)
export const deleteAdminModelLevel = (id) => apiDelete(`/admin/model-config/levels/${id}`)
export const setAdminDefaultModel = (modelId) => apiPatch('/admin/model-config/default-model', { model_id: modelId })
export const setAdminDefaultLevel = (levelId) => apiPatch('/admin/model-config/default-level', { level_id: levelId })
export const updateAdminUserModelLevel = (id, levelId) => apiPatch(`/admin/users/${id}/model-level`, { level_id: levelId })
