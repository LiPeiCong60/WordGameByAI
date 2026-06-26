import { defineStore } from 'pinia'
import { getGame } from '../api/games'
import { getStoryWorlds } from '../api/worlds'

export const useGameStore = defineStore('game', {
  state: () => ({
    currentGameId: Number(localStorage.getItem('currentGameId')) || null,
    currentGame: null,
    currentWorld: null
  }),
  actions: {
    setCurrentGameId(id) {
      this.currentGameId = Number(id)
      localStorage.setItem('currentGameId', String(id))
    },
    async loadCurrentGame(id = this.currentGameId) {
      if (!id) return null
      this.setCurrentGameId(id)
      try {
        this.currentGame = await getGame(id)
        const worlds = await getStoryWorlds(id)
        this.currentWorld = worlds.find((world) => world.id === this.currentGame.current_story_world_id) || worlds[0] || null
        return this.currentGame
      } catch (error) {
        if (error?.response?.status === 404) {
          this.clear()
          return null
        }
        throw error
      }
    },
    clear() {
      this.currentGameId = null
      this.currentGame = null
      this.currentWorld = null
      localStorage.removeItem('currentGameId')
    }
  }
})
