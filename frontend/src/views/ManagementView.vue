<template>
  <SaveContextBar v-if="activeKey !== 'list'" @changed="handleGameChanged" />
  <section v-if="activeKey === 'list'" class="save-list-workspace">
    <GameListView />
  </section>
  <NoGamePrompt v-else-if="!gameStore.currentGameId" />
  <section v-else class="save-workspace">
    <div class="save-workspace-main">
      <section class="panel save-workspace-header">
        <div>
          <span class="step-badge">存档工作台</span>
          <h1>{{ gameStore.currentGame?.title || '当前存档' }}</h1>
          <p>{{ gameStore.currentGame?.genre || '未设置题材' }} · {{ gameStore.currentGame?.world_type || '未设置世界类型' }}</p>
        </div>
        <button type="button" class="icon-button" title="刷新" @click="load">
          <RefreshCw :size="17" />
        </button>
      </section>

      <nav class="workspace-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeKey === tab.key }"
          @click="selectTab(tab.key)"
        >
          <component :is="tab.icon" :size="16" />
          {{ tab.label }}
        </button>
      </nav>

      <section v-if="activeKey === 'save'" class="panel">
        <header class="panel-header">
          <h1>存档信息</h1>
          <span>标题、题材、文风和当前状态都属于这个存档</span>
        </header>
        <form class="form-grid" @submit.prevent="saveCurrentGame">
          <label class="field"><span>标题</span><input v-model="saveForm.title" required /></label>
          <label class="field"><span>题材</span><input v-model="saveForm.genre" /></label>
          <label class="field"><span>世界类型</span><input v-model="saveForm.world_type" /></label>
          <label class="field"><span>基调</span><input v-model="saveForm.tone" /></label>
          <label class="field"><span>叙事视角</span><input v-model="saveForm.narrative_perspective" /></label>
          <label class="field wide"><span>当前状态</span><textarea v-model="saveForm.current_state" rows="3" /></label>
          <label class="field wide"><span>文风规则</span><textarea v-model="saveForm.style_guide" rows="4" /></label>
          <label class="field wide"><span>世界规则摘要</span><textarea v-model="saveForm.rules_summary" rows="4" /></label>
          <button type="submit" class="primary"><SaveIcon :size="17" />保存存档</button>
          <button type="button" @click="resetSaveForm"><RotateCcw :size="17" />重置</button>
          <button type="button" @click="downloadCurrentSave"><Download :size="17" />导出</button>
          <button type="button" @click="removeCurrentGame"><Trash2 :size="17" />删除存档</button>
        </form>
        <article v-if="lastResult" class="proposal-card">
          <h3>执行结果</h3>
          <pre>{{ JSON.stringify(lastResult, null, 2) }}</pre>
        </article>
      </section>

      <component
        v-else
        :is="activeTab.component"
        :key="`${gameStore.currentGameId}-${activeKey}-${refreshKey}`"
        embedded
      />
    </div>

    <aside class="save-workspace-side">
      <ManagementAgentPanel
        v-model:session-id="sessionId"
        v-model:scope="scope"
        v-model:message="message"
        :sessions="sessions"
        :scopes="scopeOptions"
        :messages="agentMessages"
        :pending="agentPending"
        @create-session="createSession"
        @send="send"
        @apply="apply"
        @reject="reject"
      />
      <section class="panel">
        <header class="panel-header">
          <h1>当前存档概览</h1>
        </header>
        <dl class="info-list">
          <div><dt>标题</dt><dd>{{ gameStore.currentGame?.title || '-' }}</dd></div>
          <div><dt>题材</dt><dd>{{ gameStore.currentGame?.genre || '-' }}</dd></div>
          <div><dt>世界类型</dt><dd>{{ gameStore.currentGame?.world_type || '-' }}</dd></div>
          <div><dt>基调</dt><dd>{{ gameStore.currentGame?.tone || '-' }}</dd></div>
          <div class="wide"><dt>当前状态</dt><dd>{{ gameStore.currentGame?.current_state || '-' }}</dd></div>
        </dl>
      </section>
    </aside>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen,
  Database,
  Download,
  Globe2,
  RefreshCw,
  RotateCcw,
  Save as SaveIcon,
  Trash2,
  Users
} from 'lucide-vue-next'
import ManagementAgentPanel from '../components/ManagementAgentPanel.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import CharacterView from './CharacterView.vue'
import GameListView from './GameListView.vue'
import LoreView from './LoreView.vue'
import WorldView from './WorldView.vue'
import { applyProposal, createManagementSession, listManagementSessions, rejectProposal, sendManagementMessage } from '../api/management'
import { deleteGame, exportGame, updateGame } from '../api/games'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'

const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()
const ui = useUiStore()
const sessions = ref([])
const sessionId = ref(0)
const scope = ref('综合管理')
const message = ref('')
const agentMessages = ref([])
const agentPending = ref(false)
const lastResult = ref(null)
const activeKey = ref('save')
const refreshKey = ref(0)
let nextAgentMessageId = 1

const tabs = [
  { key: 'list', label: '存档列表', scope: '综合管理', icon: Database },
  { key: 'save', label: '存档', scope: '存档', icon: Database },
  { key: 'characters', label: '角色', scope: '角色', icon: Users, component: CharacterView },
  { key: 'worlds', label: '世界', scope: '世界', icon: Globe2, component: WorldView },
  { key: 'lore', label: '设定', scope: '设定', icon: BookOpen, component: LoreView }
]

const scopeOptions = [
  { value: '综合管理', label: '综合管理' },
  ...tabs.filter((tab) => tab.key !== 'list').map((tab) => ({ value: tab.scope, label: tab.label })),
  { value: '模板', label: '模板' }
]

const activeTab = computed(() => tabs.find((tab) => tab.key === activeKey.value) || tabs[0])

const blankSaveForm = () => ({
  title: '',
  genre: '',
  world_type: '',
  tone: '',
  narrative_perspective: '第二人称',
  style_guide: '',
  rules_summary: '',
  current_state: ''
})
const saveForm = reactive(blankSaveForm())

function syncSaveForm() {
  Object.assign(saveForm, blankSaveForm(), gameStore.currentGame || {})
}

function resetTransientState() {
  agentMessages.value = []
  agentPending.value = false
  lastResult.value = null
}

function addAgentMessage(role, text, extra = {}) {
  agentMessages.value.push({
    id: nextAgentMessageId++,
    role,
    text,
    scope: role === 'user' ? scope.value : '',
    ...extra
  })
}

function clearAgentProposal(proposalId) {
  agentMessages.value = agentMessages.value.map((item) => (
    item.proposal?.proposal_id === proposalId ? { ...item, proposal: null } : item
  ))
}

function selectTab(key) {
  const tab = tabs.find((item) => item.key === key) || tabs[0]
  activeKey.value = tab.key
  scope.value = tab.scope
  router.replace({ path: '/management', query: tab.key === 'list' ? {} : { tab: tab.key } })
}

async function ensureSession(force = false) {
  if (!gameStore.currentGameId) return
  const title = '存档管理对话'
  sessions.value = await listManagementSessions(gameStore.currentGameId)
  const existing = sessions.value.find((item) => item.title === title)
  if (!force && existing) {
    sessionId.value = existing.id
    return
  }
  const created = await createManagementSession(gameStore.currentGameId, { title })
  sessionId.value = created.id
  sessions.value = await listManagementSessions(gameStore.currentGameId)
}

async function load() {
  await ui.run(async () => {
    if (!gameStore.currentGameId) return
    await gameStore.loadCurrentGame()
    syncSaveForm()
    await ensureSession()
  })
}

async function handleGameChanged() {
  sessionId.value = 0
  refreshKey.value += 1
  resetTransientState()
  await load()
}

async function createSession() {
  await ui.run(async () => {
    resetTransientState()
    await ensureSession(true)
  })
}

async function send() {
  const outgoing = message.value.trim()
  if (!outgoing || agentPending.value) return
  if (!sessionId.value) await ensureSession()
  if (!sessionId.value) return
  addAgentMessage('user', outgoing)
  message.value = ''
  lastResult.value = null
  agentPending.value = true
  try {
    await ui.run(async () => {
      const result = await sendManagementMessage(sessionId.value, outgoing, scope.value)
      addAgentMessage('assistant', result.reply || '已收到。', {
        proposal: result.requires_confirmation ? result : null
      })
    })
  } catch (error) {
    addAgentMessage('assistant', ui.error || error?.message || '请求失败。')
  } finally {
    agentPending.value = false
  }
}

async function apply(id) {
  await ui.run(async () => {
    lastResult.value = await applyProposal(id)
    clearAgentProposal(id)
    addAgentMessage('status', '方案已执行。', { result: lastResult.value })
    await gameStore.loadCurrentGame()
    syncSaveForm()
    refreshKey.value += 1
  })
}

async function reject(id) {
  await ui.run(async () => {
    lastResult.value = await rejectProposal(id)
    clearAgentProposal(id)
    addAgentMessage('status', '方案已拒绝。', { result: lastResult.value })
  })
}

async function saveCurrentGame() {
  await ui.run(async () => {
    await updateGame(gameStore.currentGameId, { ...saveForm })
    await gameStore.loadCurrentGame()
    syncSaveForm()
    lastResult.value = { ok: true, status: 'saved' }
  })
}

function resetSaveForm() {
  syncSaveForm()
}

async function downloadCurrentSave() {
  const data = await exportGame(gameStore.currentGameId)
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `narrative-agent-save-${gameStore.currentGameId}.json`
  link.click()
  URL.revokeObjectURL(url)
}

async function removeCurrentGame() {
  if (!window.confirm('确定彻底删除当前存档吗？角色、世界、设定和剧情记录都会一起删除。')) return
  await ui.run(async () => {
    await deleteGame(gameStore.currentGameId)
    gameStore.clear()
    router.push('/')
  })
}

watch(
  () => route.query.tab,
  (tab) => {
    const key = typeof tab === 'string' ? tab : (gameStore.currentGameId ? 'save' : 'list')
    const match = tabs.find((item) => item.key === key) || tabs[0]
    activeKey.value = match.key
    scope.value = match.scope
  },
  { immediate: true }
)

onMounted(load)
</script>
