<template>
  <section class="save-context">
    <div class="save-context-identity">
      <span class="save-context-icon"><BookOpen :size="21" /></span>
      <div>
        <span class="step-badge">当前存档</span>
        <h2>{{ gameStore.currentGame?.title || '未选择存档' }}</h2>
        <p>
          {{ gameStore.currentGame?.genre || '请选择一个存档' }}
          <span v-if="gameStore.currentGame?.world_type"> · {{ gameStore.currentGame.world_type }}</span>
        </p>
      </div>
    </div>
    <div class="save-context-actions">
      <select v-model.number="selectedGameId" @change="switchGame">
        <option :value="0">选择存档</option>
        <option v-for="game in games" :key="game.id" :value="game.id">
          {{ game.title }}{{ game.genre ? ` · ${game.genre}` : '' }}
        </option>
      </select>
      <RouterLink class="secondary-link" to="/management?tab=list">存档列表</RouterLink>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { BookOpen } from 'lucide-vue-next'
import { listGames } from '../api/games'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'

const emit = defineEmits(['changed'])
const gameStore = useGameStore()
const ui = useUiStore()
const games = ref([])
const selectedGameId = ref(gameStore.currentGameId || 0)

async function loadGames() {
  games.value = await listGames()
  if (gameStore.currentGameId) {
    selectedGameId.value = gameStore.currentGameId
    await gameStore.loadCurrentGame()
  }
}

async function switchGame() {
  if (!selectedGameId.value) {
    gameStore.clear()
    emit('changed')
    return
  }
  await ui.run(async () => {
    await gameStore.loadCurrentGame(selectedGameId.value)
    emit('changed')
  })
}

watch(
  () => gameStore.currentGameId,
  (id) => {
    selectedGameId.value = id || 0
  }
)

onMounted(loadGames)
</script>
