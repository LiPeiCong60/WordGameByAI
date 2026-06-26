import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export const listEvents = (gameId) => apiGet(`/games/${gameId}/events`)
export const createEvent = (gameId, data) => apiPost(`/games/${gameId}/events`, data)
export const updateEvent = (id, data) => apiPatch(`/events/${id}`, data)
export const deleteEvent = (id) => apiDelete(`/events/${id}`)
