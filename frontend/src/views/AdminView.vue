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
          <label class="compact-field model-level-field">
            <span>模型等级</span>
            <select :value="user.model_level_id || ''" :disabled="pendingUserId === user.id" @change="saveUserModelLevel(user, $event.target.value)">
              <option value="">默认等级</option>
              <option v-for="level in modelConfig.levels" :key="level.id" :value="level.id">{{ level.label || level.id }}</option>
            </select>
          </label>
          <span v-if="pendingUserId === user.id">正在保存...</span>
          <label class="compact-field">
            <span>每日上限</span>
            <input v-model.number="quotaDrafts[user.id]" type="number" min="0" />
          </label>
          <div class="inline-actions">
            <button type="button" :disabled="pendingUserId === user.id" @click="toggleUserActive(user)">{{ user.is_active ? '停用' : '启用' }}</button>
            <button type="button" :disabled="pendingUserId === user.id" @click="toggleUserAdmin(user)">{{ user.is_admin ? '取消管理员' : '设为管理员' }}</button>
            <button type="button" :disabled="pendingUserId === user.id" @click="toggleUserMember(user)">{{ user.is_member ? '取消会员' : '设为会员' }}</button>
            <button type="button" :disabled="pendingUserId === user.id" @click="saveUserQuota(user)">{{ quotaSaveLabel(user) }}</button>
          </div>
        </article>
      </div>

      <h2 class="section-title">模型池</h2>
      <form class="admin-form" @submit.prevent="saveModel">
        <label class="field"><span>配置 ID</span><input v-model.trim="modelForm.id" required placeholder="deepseek_chat" /></label>
        <label class="field"><span>显示名称</span><input v-model.trim="modelForm.label" placeholder="DeepSeek Chat" /></label>
        <label class="field"><span>Base URL</span><input v-model.trim="modelForm.base_url" placeholder="https://api.deepseek.com" /></label>
        <label class="field"><span>模型名</span><input v-model.trim="modelForm.model" placeholder="deepseek-chat" /></label>
        <label class="field"><span>Temperature</span><input v-model.number="modelForm.temperature" type="number" min="0" max="2" step="0.1" /></label>
        <label class="field"><span>API Key</span><input v-model.trim="modelForm.api_key" type="password" autocomplete="new-password" placeholder="留空则保留服务器现有密钥" /></label>
        <label class="check-field"><input v-model="modelForm.enabled" type="checkbox" />启用</label>
        <label class="check-field"><input v-model="modelForm.clear_api_key" type="checkbox" />清除已保存密钥</label>
        <button type="submit" class="primary">保存模型配置</button>
      </form>
      <div class="admin-list">
        <article v-for="model in modelConfig.models" :key="model.id">
          <strong>{{ model.label || model.id }}</strong>
          <span>{{ model.model || '-' }} · {{ model.base_url || '-' }}</span>
          <em>{{ model.enabled ? '启用' : '停用' }} · {{ model.has_api_key ? '已配置密钥' : '未配置密钥' }}</em>
          <div class="inline-actions">
            <button type="button" @click="editModel(model)">编辑</button>
            <button type="button" @click="saveDefaultModel(model.id)">{{ modelConfig.default_model_id === model.id ? '全局默认' : '设为兜底模型' }}</button>
            <button type="button" @click="removeModel(model)">删除</button>
          </div>
        </article>
      </div>

      <h2 class="section-title">模型等级 / Agent 分配</h2>
      <form class="admin-form level-form" @submit.prevent="saveLevel">
        <label class="field"><span>等级 ID</span><input v-model.trim="levelForm.id" required placeholder="free" /></label>
        <label class="field"><span>等级名称</span><input v-model.trim="levelForm.label" placeholder="普通用户档" /></label>
        <label class="field"><span>兜底模型</span><select v-model="levelForm.fallback_model_id"><option value="">使用全局兜底</option><option v-for="model in modelConfig.models" :key="model.id" :value="model.id">{{ model.label || model.id }}</option></select></label>
        <label class="field wide"><span>说明</span><textarea v-model.trim="levelForm.description" rows="2" /></label>
        <div class="agent-model-grid wide">
          <label v-for="agent in modelConfig.agent_names" :key="agent" class="field">
            <span>{{ agent }}</span>
            <select v-model="levelForm.agent_models[agent]">
              <option value="">使用等级兜底</option>
              <option v-for="model in modelConfig.models" :key="model.id" :value="model.id">{{ model.label || model.id }}</option>
            </select>
          </label>
        </div>
        <button type="submit" class="primary">保存等级</button>
      </form>
      <div class="admin-list">
        <article v-for="level in modelConfig.levels" :key="level.id">
          <strong>{{ level.label || level.id }}</strong>
          <span>{{ level.description || '未填写说明' }}</span>
          <em>兜底：{{ modelLabel(level.fallback_model_id) }} · Agent 覆盖 {{ Object.keys(level.agent_models || {}).length }} 个</em>
          <div class="inline-actions">
            <button type="button" @click="editLevel(level)">编辑</button>
            <button type="button" @click="saveDefaultLevel(level.id)">{{ modelConfig.default_level_id === level.id ? '默认等级' : '设为默认等级' }}</button>
            <button type="button" @click="removeLevel(level)">删除</button>
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
import {
  deleteAdminModel,
  deleteAdminModelLevel,
  getAdminModelConfig,
  getAdminSummary,
  listAdminGames,
  listAdminUsers,
  saveAdminModel,
  saveAdminModelLevel,
  setAdminDefaultLevel,
  setAdminDefaultModel,
  updateAdminUser,
  updateAdminUserModelLevel
} from '../api/admin'
import { useUiStore } from '../stores/uiStore'

const ui = useUiStore()
const summary = ref({})
const users = ref([])
const games = ref([])
const quotaDrafts = ref({})
const pendingUserId = ref(null)
const modelConfig = ref({ models: [], levels: [], agent_names: [], user_levels: {} })
const modelForm = ref(emptyModelForm())
const levelForm = ref(emptyLevelForm())

async function load() {
  await ui.run(async () => {
    summary.value = await getAdminSummary()
    modelConfig.value = await getAdminModelConfig()
    users.value = await listAdminUsers()
    quotaDrafts.value = Object.fromEntries(users.value.map((user) => [user.id, user.daily_message_limit ?? 20]))
    games.value = await listAdminGames()
  })
}

async function updateUser(user, data) {
  pendingUserId.value = user.id
  try {
    await ui.run(async () => {
      await updateAdminUser(user.id, data)
      users.value = await listAdminUsers()
      quotaDrafts.value = Object.fromEntries(users.value.map((item) => [item.id, item.daily_message_limit ?? 20]))
      const refreshed = users.value.find((item) => item.id === user.id)
      if (!refreshed || !matchesExpectedUpdate(refreshed, data)) {
        throw new Error('用户设置没有生效，请确认服务器后端已更新并重启。')
      }
    })
  } finally {
    pendingUserId.value = null
  }
}

async function toggleUserActive(user) {
  await updateUser(user, { is_active: !user.is_active })
}

async function toggleUserAdmin(user) {
  await updateUser(user, { is_admin: !user.is_admin })
}

async function toggleUserMember(user) {
  const quota = normalizedQuotaDraft(user)
  const nextIsMember = !user.is_member
  await updateUser(user, {
    is_member: nextIsMember,
    daily_message_limit: nextIsMember ? quota : Math.min(quota || 20, 20)
  })
}

async function saveUserQuota(user) {
  const quota = normalizedQuotaDraft(user)
  const data = { daily_message_limit: quota }
  if (!user.is_admin && !user.is_member && (quota === 0 || quota > 20)) {
    data.is_member = true
  }
  await updateUser(user, data)
}

async function saveUserModelLevel(user, levelId) {
  pendingUserId.value = user.id
  try {
    await ui.run(async () => {
      await updateAdminUserModelLevel(user.id, levelId)
      modelConfig.value = await getAdminModelConfig()
      users.value = await listAdminUsers()
    })
  } finally {
    pendingUserId.value = null
  }
}

async function saveModel() {
  await ui.run(async () => {
    await saveAdminModel(modelForm.value)
    modelConfig.value = await getAdminModelConfig()
    users.value = await listAdminUsers()
    modelForm.value = emptyModelForm()
  })
}

async function removeModel(model) {
  if (!window.confirm(`确定删除模型配置 ${model.label || model.id}？`)) return
  await ui.run(async () => {
    await deleteAdminModel(model.id)
    modelConfig.value = await getAdminModelConfig()
  })
}

async function saveDefaultModel(modelId) {
  await ui.run(async () => {
    modelConfig.value = await setAdminDefaultModel(modelId)
  })
}

function editModel(model) {
  modelForm.value = {
    id: model.id,
    label: model.label || '',
    base_url: model.base_url || '',
    model: model.model || '',
    api_key: '',
    clear_api_key: false,
    temperature: Number(model.temperature ?? 0.7),
    enabled: Boolean(model.enabled)
  }
}

async function saveLevel() {
  await ui.run(async () => {
    await saveAdminModelLevel({
      ...levelForm.value,
      agent_models: cleanAgentModels(levelForm.value.agent_models)
    })
    modelConfig.value = await getAdminModelConfig()
    users.value = await listAdminUsers()
    levelForm.value = emptyLevelForm()
  })
}

async function removeLevel(level) {
  if (!window.confirm(`确定删除模型等级 ${level.label || level.id}？`)) return
  await ui.run(async () => {
    await deleteAdminModelLevel(level.id)
    modelConfig.value = await getAdminModelConfig()
    users.value = await listAdminUsers()
  })
}

async function saveDefaultLevel(levelId) {
  await ui.run(async () => {
    modelConfig.value = await setAdminDefaultLevel(levelId)
  })
}

function editLevel(level) {
  levelForm.value = {
    id: level.id,
    label: level.label || '',
    description: level.description || '',
    fallback_model_id: level.fallback_model_id || '',
    agent_models: { ...(level.agent_models || {}) }
  }
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

function normalizedQuotaDraft(user) {
  const value = Number(quotaDrafts.value[user.id] ?? user.daily_message_limit ?? 20)
  return Number.isFinite(value) && value >= 0 ? Math.floor(value) : 20
}

function quotaSaveLabel(user) {
  const quota = normalizedQuotaDraft(user)
  if (!user.is_admin && !user.is_member && (quota === 0 || quota > 20)) return '保存并设为会员'
  return '保存额度'
}

function matchesExpectedUpdate(user, data) {
  if (Object.prototype.hasOwnProperty.call(data, 'is_active') && Boolean(user.is_active) !== Boolean(data.is_active)) return false
  if (Object.prototype.hasOwnProperty.call(data, 'is_admin') && Boolean(user.is_admin) !== Boolean(data.is_admin)) return false
  if (Object.prototype.hasOwnProperty.call(data, 'is_member') && Boolean(user.is_member) !== Boolean(data.is_member)) return false
  if (
    Object.prototype.hasOwnProperty.call(data, 'daily_message_limit') &&
    Number(user.daily_message_limit) !== Number(data.daily_message_limit)
  ) return false
  return true
}

function emptyModelForm() {
  return {
    id: '',
    label: '',
    base_url: '',
    model: '',
    api_key: '',
    clear_api_key: false,
    temperature: 0.7,
    enabled: true
  }
}

function emptyLevelForm() {
  return {
    id: '',
    label: '',
    description: '',
    fallback_model_id: '',
    agent_models: {}
  }
}

function cleanAgentModels(agentModels) {
  return Object.fromEntries(Object.entries(agentModels || {}).filter(([, value]) => Boolean(value)))
}

function modelLabel(modelId) {
  if (!modelId) return '全局兜底'
  const model = modelConfig.value.models.find((item) => item.id === modelId)
  return model?.label || modelId
}

onMounted(load)
</script>
