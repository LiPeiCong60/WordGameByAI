import { apiDelete, apiGet, apiPatch, apiPost, uploadFile } from './http'

export const listCharacters = (gameId) => apiGet(`/games/${gameId}/characters`)
export const createCharacter = (gameId, data) => apiPost(`/games/${gameId}/characters`, data)
export const updateCharacter = (id, data) => apiPatch(`/characters/${id}`, data)
export const deleteCharacter = (id) => apiDelete(`/characters/${id}`)
export const uploadAvatar = (id, file) => uploadFile(`/characters/${id}/avatar`, file)
export const listCharacterInventory = (id) => apiGet(`/characters/${id}/inventory`)
