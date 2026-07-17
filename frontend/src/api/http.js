import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
})

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
let refreshPromise = null

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('authRefreshToken')
  if (!refreshToken) throw new Error('没有可用的刷新凭证。')
  if (!refreshPromise) {
    refreshPromise = axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
      .then((response) => {
        localStorage.setItem('authToken', response.data.token)
        localStorage.setItem('authRefreshToken', response.data.refresh_token)
        localStorage.setItem('authUser', JSON.stringify(response.data.user))
        return response.data.token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

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
  async (error) => {
    const config = error?.config
    const refreshToken = localStorage.getItem('authRefreshToken')
    if (error?.response?.status === 401 && refreshToken && config && !config._authRetried && !config.url?.includes('/auth/refresh')) {
      config._authRetried = true
      try {
        await refreshAccessToken()
        return api(config)
      } catch {
        localStorage.removeItem('authRefreshToken')
      } finally {
        refreshPromise = null
      }
    }
    if (error?.response?.status === 401) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('authRefreshToken')
      localStorage.removeItem('authUser')
    }
    return Promise.reject(error)
  }
)

export const apiGet = (url, config) => api.get(url, config)
export const apiPost = (url, data, config) => api.post(url, data, config)
export const apiPut = (url, data, config) => api.put(url, data, config)
export const apiPatch = (url, data, config) => api.patch(url, data, config)
export const apiDelete = (url, config) => api.delete(url, config)

export async function authorizedFetch(url, options = {}) {
  const request = () => fetch(url, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() }
  })
  let response = await request()
  if (response.status !== 401 || !localStorage.getItem('authRefreshToken')) return response
  try {
    await refreshAccessToken()
    response = await request()
  } catch {
    localStorage.removeItem('authToken')
    localStorage.removeItem('authRefreshToken')
    localStorage.removeItem('authUser')
  }
  return response
}

export function uploadFile(url, file) {
  const data = new FormData()
  data.append('file', file)
  return api.post(url, data, { headers: { 'Content-Type': 'multipart/form-data' } })
}
