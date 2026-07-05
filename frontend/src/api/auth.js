import { apiGet, apiPost } from './http'

export const getCaptcha = () => apiGet('/auth/captcha')
export const register = (data) => apiPost('/auth/register', data)
export const login = (data) => apiPost('/auth/login', data)
export const getMe = () => apiGet('/auth/me')
