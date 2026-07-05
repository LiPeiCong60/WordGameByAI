import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
})

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export function authHeaders() {
  const token = localStorage.getItem('authToken')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

api.interceptors.request.use((config) => {
  config.headers = { ...(config.headers || {}), ...authHeaders() }
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('authUser')
    }
    return Promise.reject(error)
  }
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
