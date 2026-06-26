import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export const listTemplates = () => apiGet('/templates')
export const createTemplate = (data) => apiPost('/templates', data)
export const updateTemplate = (id, data) => apiPatch(`/templates/${id}`, data)
export const deleteTemplate = (id) => apiDelete(`/templates/${id}`)
