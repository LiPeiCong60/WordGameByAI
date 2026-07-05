<template>
  <section class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>管理后台</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <div class="stat-grid">
        <div><span>用户</span><strong>{{ summary.users ?? '-' }}</strong></div>
        <div><span>存档</span><strong>{{ summary.games ?? '-' }}</strong></div>
        <div><span>回合</span><strong>{{ summary.turns ?? '-' }}</strong></div>
        <div><span>待确认</span><strong>{{ summary.pending_proposals ?? '-' }}</strong></div>
      </div>
      <h2 class="section-title">用户</h2>
      <div class="admin-list">
        <article v-for="user in users" :key="user.id">
          <strong>{{ user.username }}</strong>
          <span>{{ user.email || '未填写邮箱' }}</span>
          <em>{{ user.is_admin ? '管理员' : '玩家' }} · {{ user.is_active ? '启用' : '停用' }}</em>
          <div class="inline-actions">
            <button type="button" @click="toggleUserActive(user)">{{ user.is_active ? '停用' : '启用' }}</button>
            <button type="button" @click="toggleUserAdmin(user)">{{ user.is_admin ? '取消管理员' : '设为管理员' }}</button>
          </div>
        </article>
      </div>
    </div>

    <div class="panel">
      <header class="panel-header"><h1>存档总览</h1></header>
      <div class="admin-list">
        <article v-for="game in games" :key="game.id">
          <strong>{{ game.title }}</strong>
          <span>{{ game.genre || '未设置题材' }} · {{ game.owner_username }}</span>
          <em>#{{ game.id }}</em>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { getAdminSummary, listAdminGames, listAdminUsers, updateAdminUser } from '../api/admin'
import { useUiStore } from '../stores/uiStore'

const ui = useUiStore()
const summary = ref({})
const users = ref([])
const games = ref([])

async function load() {
  await ui.run(async () => {
    summary.value = await getAdminSummary()
    users.value = await listAdminUsers()
    games.value = await listAdminGames()
  })
}

async function updateUser(user, data) {
  await ui.run(async () => {
    const updated = await updateAdminUser(user.id, data)
    users.value = users.value.map((item) => (item.id === updated.id ? updated : item))
  }, '用户状态已更新')
}

function toggleUserActive(user) {
  updateUser(user, { is_active: !user.is_active })
}

function toggleUserAdmin(user) {
  updateUser(user, { is_admin: !user.is_admin })
}

onMounted(load)
</script>
