import { defineStore } from 'pinia'
import { getMe, login, logoutSession, register } from '../api/auth'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem('authUser') || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('authToken') || '',
    user: readUser()
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
    isAdmin: (state) => Boolean(state.user?.is_admin)
  },
  actions: {
    setSession(session) {
      this.token = session.token
      this.user = session.user
      localStorage.setItem('authToken', session.token)
      if (session.refresh_token) localStorage.setItem('authRefreshToken', session.refresh_token)
      localStorage.setItem('authUser', JSON.stringify(session.user))
    },
    async login(payload) {
      this.setSession(await login(payload))
    },
    async register(payload) {
      this.setSession(await register(payload))
    },
    async refreshMe() {
      if (!this.token) return null
      this.user = await getMe()
      localStorage.setItem('authUser', JSON.stringify(this.user))
      return this.user
    },
    async logout() {
      try {
        if (this.token) await logoutSession(localStorage.getItem('authRefreshToken') || '')
      } catch {
        // Local logout must still succeed if the network is unavailable.
      }
      this.token = ''
      this.user = null
      localStorage.removeItem('authToken')
      localStorage.removeItem('authRefreshToken')
      localStorage.removeItem('authUser')
      localStorage.removeItem('currentGameId')
    }
  }
})
