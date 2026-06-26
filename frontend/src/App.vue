<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">NA</span>
        <span>NarrativeAgent</span>
      </RouterLink>
      <nav>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="status-strip" v-if="gameStore.currentGame">
        <strong>{{ gameStore.currentGame.title }}</strong>
        <span>{{ gameStore.currentGame.genre || '未设置题材' }}</span>
      </div>
    </aside>
    <main class="main-view">
      <RouterView />
    </main>
    <div v-if="ui.error" class="toast error" @click="ui.clearError">{{ ui.error }}</div>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { Compass, Database, Settings } from 'lucide-vue-next'
import { useGameStore } from './stores/gameStore'
import { useUiStore } from './stores/uiStore'

const gameStore = useGameStore()
const ui = useUiStore()

const navItems = [
  { to: '/management', label: '存档', icon: Database },
  { to: '/play', label: '游戏', icon: Compass },
  { to: '/templates', label: '模板', icon: Settings }
]
</script>
