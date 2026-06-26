import { apiGet, apiPost } from './http'

export const createManagementSession = (gameId, data) => apiPost(`/games/${gameId}/management/sessions`, data)
export const listManagementSessions = (gameId) => apiGet(`/games/${gameId}/management/sessions`)
export const sendManagementMessage = (sessionId, message, scope = '') => apiPost(`/management/sessions/${sessionId}/chat`, { message, scope })
export const getProposal = (id) => apiGet(`/management/proposals/${id}`)
export const applyProposal = (id) => apiPost(`/management/proposals/${id}/apply`)
export const rejectProposal = (id) => apiPost(`/management/proposals/${id}/reject`)
