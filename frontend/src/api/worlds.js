import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export const getStoryWorlds = (gameId) => apiGet(`/games/${gameId}/story-worlds`)
export const createStoryWorld = (gameId, data) => apiPost(`/games/${gameId}/story-worlds`, data)
export const updateStoryWorld = (id, data) => apiPatch(`/story-worlds/${id}`, data)
export const deleteStoryWorld = (id) => apiDelete(`/story-worlds/${id}`)
export const setCurrentStoryWorld = (gameId, worldId) => apiPost(`/games/${gameId}/story-worlds/${worldId}/set-current`)
