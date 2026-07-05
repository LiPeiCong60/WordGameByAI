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
          <em>
            {{ user.is_admin ? '管理员' : '玩家' }} · {{ user.is_member ? '会员' : '非会员' }} ·
            {{ user.is_active ? '启用' : '停用' }} ·
            {{ quotaLabel(user) }}
          </em>
          <span>{{ usageLabel(user) }}</span>
          <label class="compact-field">
            <span>每日上限</span>
            <input v-model.number="quotaDrafts[user.id]" type="number" min="0" :max="user.is_member ? undefined : 20" />
          </label>
          <div class="inline-actions">
            <button type="button" @click="toggleUserActive(user)">{{ user.is_active ? '停用' : '启用' }}</button>
            <button type="button" @click="toggleUserAdmin(user)">{{ user.is_admin ? '取消管理员' : '设为管理员' }}</button>
            <button type="button" @click="toggleUserMember(user)">{{ user.is_member ? '取消会员' : '设为会员' }}</button>
            <button type="button" @click="saveUserQuota(user)">保存额度</button>
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
const quotaDrafts = ref({})

async function load() {
  await ui.run(async () => {
    summary.value = await getAdminSummary()
    users.value = await listAdminUsers()
    quotaDrafts.value = Object.fromEntries(users.value.map((user) => [user.id, user.daily_message_limit ?? 20]))
    games.value = await listAdminGames()
  })
}

async function updateUser(user, data) {
  await ui.run(async () => {
    const updated = await updateAdminUser(user.id, data)
    users.value = users.value.map((item) => (item.id === updated.id ? updated : item))
    quotaDrafts.value = { ...quotaDrafts.value, [updated.id]: updated.daily_message_limit ?? 20 }
  }, '用户状态已更新')
}

function toggleUserActive(user) {
  updateUser(user, { is_active: !user.is_active })
}

function toggleUserAdmin(user) {
  updateUser(user, { is_admin: !user.is_admin })
}

function toggleUserMember(user) {
  updateUser(user, { is_member: !user.is_member })
}

function saveUserQuota(user) {
  updateUser(user, { daily_message_limit: Number(quotaDrafts.value[user.id] ?? 20) })
}

function quotaLabel(user) {
  if (user.is_admin) return '不限额'
  const effective = resolveEffectiveLimit(user)
  return effective === null ? '不限额' : `每日 ${effective} 条`
}

function usageLabel(user) {
  if (user.is_admin) return '今日已用：不限额'
  const effective = resolveEffectiveLimit(user)
  const used = Number(user.today_message_count ?? 0)
  if (effective === null) return `今日已用：${used} 条`
  const remaining = Number(user.remaining_message_count ?? Math.max(effective - used, 0))
  return `今日已用：${used}/${effective}，剩余 ${remaining}`
}

function resolveEffectiveLimit(user) {
  if (user.is_admin) return null
  if (user.effective_daily_message_limit !== undefined) {
    return user.effective_daily_message_limit === null ? null : Number(user.effective_daily_message_limit)
  }
  const configured = Number(user.daily_message_limit ?? 20)
  if (user.is_member) return configured > 0 ? configured : null
  return Math.min(Math.max(configured, 0), 20)
}

onMounted(load)
</script>
