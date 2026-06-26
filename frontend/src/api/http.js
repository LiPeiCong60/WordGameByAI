import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
})

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

api.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
)

export const apiGet = (url, config) => api.get(url, config)
export const apiPost = (url, data, config) => api.post(url, data, config)
export const apiPatch = (url, data, config) => api.patch(url, data, config)
export const apiDelete = (url, config) => api.delete(url, config)

export function uploadFile(url, file) {
  const data = new FormData()
  data.append('file', file)
  return api.post(url, data, { headers: { 'Content-Type': 'multipart/form-data' } })
}
