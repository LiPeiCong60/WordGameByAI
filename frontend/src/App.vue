<template>
  <div :class="['app-shell', { 'auth-shell': !auth.isAuthenticated }]">
    <aside v-if="auth.isAuthenticated" class="sidebar">
      <RouterLink class="brand" to="/management" aria-label="World Game by AI 首页">
        <img class="brand-logo" src="/assets/brand/app_icon.webp" alt="" />
        <span class="brand-copy">
          <strong>World Game</strong>
          <small>by AI · 无限叙事</small>
        </span>
      </RouterLink>

      <nav class="desktop-nav" aria-label="主导航">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
          <span class="nav-icon"><component :is="item.icon" :size="19" /></span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <RouterLink v-if="gameStore.currentGame" class="current-story-card" to="/play">
        <span class="eyebrow">正在创作</span>
        <strong>{{ gameStore.currentGame.title }}</strong>
        <small>{{ gameStore.currentGame.genre || '自由题材' }} · 继续故事 →</small>
      </RouterLink>

      <div class="account-strip">
        <span class="account-avatar">{{ accountInitial }}</span>
        <span class="account-copy">
          <strong>{{ auth.user?.username || '玩家' }}</strong>
          <small>{{ auth.isAdmin ? '管理员' : '故事创作者' }}</small>
        </span>
        <button type="button" class="icon-button sidebar-logout" title="退出登录" aria-label="退出登录" @click="logout">
          <LogOut :size="17" />
        </button>
      </div>
    </aside>

    <main class="main-view">
      <header v-if="auth.isAuthenticated" class="mobile-app-bar">
        <RouterLink class="mobile-brand" to="/management">
          <img src="/assets/brand/app_icon.webp" alt="" />
          <span>World Game by AI</span>
        </RouterLink>
        <button type="button" class="icon-button" title="退出登录" aria-label="退出登录" @click="logout">
          <LogOut :size="18" />
        </button>
      </header>
      <RouterView />
    </main>

    <nav v-if="auth.isAuthenticated" class="mobile-nav" aria-label="移动端主导航">
      <RouterLink v-for="item in navItems" :key="`mobile-${item.to}`" :to="item.to">
        <component :is="item.icon" :size="21" />
        <span>{{ item.shortLabel || item.label }}</span>
      </RouterLink>
    </nav>

    <div v-if="ui.error" class="toast error" role="alert">
      <span>{{ ui.error }}</span>
      <button type="button" class="toast-close" aria-label="关闭提示" @click="ui.clearError">×</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { Compass, Database, LogOut, Settings, Shield } from 'lucide-vue-next'
import { useAuthStore } from './stores/authStore'
import { useGameStore } from './stores/gameStore'
import { useUiStore } from './stores/uiStore'

const gameStore = useGameStore()
const ui = useUiStore()
const auth = useAuthStore()
const router = useRouter()

const accountInitial = computed(() => String(auth.user?.username || 'W').slice(0, 1).toUpperCase())
const navItems = computed(() => [
  { to: '/management', label: '我的存档', shortLabel: '存档', icon: Database },
  { to: '/play', label: '剧情创作', shortLabel: '剧情', icon: Compass },
  { to: '/templates', label: '故事模板', shortLabel: '模板', icon: Settings },
  ...(auth.isAdmin ? [{ to: '/admin', label: '系统管理', shortLabel: '管理', icon: Shield }] : [])
])

async function logout() {
  await auth.logout()
  gameStore.clear()
  router.push('/login')
}
</script>
