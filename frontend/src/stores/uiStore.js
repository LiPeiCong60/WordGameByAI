import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({
    loading: false,
    pendingCount: 0,
    error: ''
  }),
  actions: {
    setError(error) {
      this.error = typeof error === 'string' ? error : error?.response?.data?.detail || error?.message || '请求失败'
    },
    clearError() {
      this.error = ''
    },
    async run(task) {
      this.pendingCount += 1
      this.loading = true
      this.error = ''
      try {
        return await task()
      } catch (error) {
        this.setError(error)
        throw error
      } finally {
        this.pendingCount = Math.max(0, this.pendingCount - 1)
        this.loading = this.pendingCount > 0
      }
    }
  }
})
