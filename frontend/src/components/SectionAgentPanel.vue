<template>
  <section class="panel management-panel section-agent">
    <header class="panel-header">
      <h2>{{ title }}</h2>
      <button type="button" class="icon-button" title="新建对话" @click="createSession">
        <Plus :size="17" />
      </button>
    </header>
    <div class="notice">
      <p>{{ description }}</p>
    </div>
    <div v-if="quickPrompts.length" class="quick-prompt-row">
      <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="message = prompt">
        {{ prompt }}
      </button>
    </div>
    <div v-if="messages.length || pending" class="agent-thread" aria-live="polite">
      <article v-for="item in messages" :key="item.id" class="chat-message" :class="`chat-message--${item.role}`">
        <div class="chat-bubble">
          <header class="chat-meta">
            <span>{{ roleLabel(item.role) }}</span>
            <small v-if="item.scope">{{ item.scope }}</small>
          </header>
          <p v-if="item.text">{{ item.text }}</p>
          <div v-if="item.proposal" class="chat-attachment">
            <h3>待确认方案 #{{ item.proposal.proposal_id }}</h3>
            <pre>{{ JSON.stringify(item.proposal.proposed_actions, null, 2) }}</pre>
            <div class="button-row">
              <button type="button" class="primary" @click="apply(item.proposal.proposal_id)">
                <Check :size="17" />
                确认执行
              </button>
              <button type="button" @click="reject(item.proposal.proposal_id)">
                <X :size="17" />
                拒绝
              </button>
            </div>
          </div>
          <div v-if="item.result" class="chat-attachment">
            <h3>执行结果</h3>
            <pre>{{ JSON.stringify(item.result, null, 2) }}</pre>
          </div>
        </div>
      </article>
      <article v-if="pending" class="chat-message chat-message--assistant">
        <div class="chat-bubble">
          <header class="chat-meta"><span>智能体</span></header>
          <p>正在整理回复...</p>
        </div>
      </article>
    </div>
    <form class="agent-composer" @submit.prevent="send">
      <textarea v-model="message" rows="4" :placeholder="placeholder" />
      <button type="submit" class="primary" :disabled="!message.trim() || pending">
        <Send :size="17" />
        发送给智能体
      </button>
    </form>
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { Check, Plus, Send, X } from 'lucide-vue-next'
import { applyProposal, createManagementSession, listManagementSessions, rejectProposal, sendManagementMessage } from '../api/management'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'

const props = defineProps({
  scope: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '和这个板块的智能体讨论，确认后才会写入数据。' },
  placeholder: { type: String, default: '描述你想新增、修改、删除或查询的数据。信息不足时，智能体会先追问。' },
  global: { type: Boolean, default: false },
  context: { type: String, default: '' },
  quickPrompts: { type: Array, default: () => [] }
})

const emit = defineEmits(['applied'])
const gameStore = useGameStore()
const ui = useUiStore()
const sessionId = ref(0)
const message = ref('')
const messages = ref([])
const pending = ref(false)
let nextMessageId = 1

function addMessage(role, text, extra = {}) {
  messages.value.push({
    id: nextMessageId++,
    role,
    text,
    scope: role === 'user' ? props.scope : '',
    ...extra
  })
}

function roleLabel(role) {
  if (role === 'user') return '你'
  if (role === 'status') return '状态'
  return '智能体'
}

function clearProposal(proposalId) {
  messages.value = messages.value.map((item) => (
    item.proposal?.proposal_id === proposalId ? { ...item, proposal: null } : item
  ))
}

async function ensureSession(force = false) {
  const gameId = props.global ? 0 : gameStore.currentGameId
  if (!props.global && !gameId) return
  await ui.run(async () => {
    const sessions = await listManagementSessions(gameId)
    const title = `${props.title}对话`
    const existing = sessions.find((item) => item.title === title)
    if (!force && existing) {
      sessionId.value = existing.id
      return
    }
    const created = await createManagementSession(gameId, { title })
    sessionId.value = created.id
  })
}

async function createSession() {
  messages.value = []
  await ensureSession(true)
}

async function send() {
  const outgoing = message.value.trim()
  if (!outgoing || pending.value) return
  if (!sessionId.value) await ensureSession()
  if (!sessionId.value) return
  addMessage('user', outgoing)
  message.value = ''
  pending.value = true
  try {
    await ui.run(async () => {
      const payload = props.context ? `【当前编辑上下文】\n${props.context}\n\n【用户请求】\n${outgoing}` : outgoing
      const result = await sendManagementMessage(sessionId.value, payload, props.scope)
      addMessage('assistant', result.reply || '已收到。', {
        proposal: result.requires_confirmation ? result : null
      })
    })
  } catch (error) {
    addMessage('assistant', ui.error || error?.message || '请求失败。')
  } finally {
    pending.value = false
  }
}

async function apply(id) {
  await ui.run(async () => {
    const result = await applyProposal(id)
    clearProposal(id)
    addMessage('status', '方案已执行。', { result })
    if (!props.global) await gameStore.loadCurrentGame()
    emit('applied')
  })
}

async function reject(id) {
  await ui.run(async () => {
    const result = await rejectProposal(id)
    clearProposal(id)
    addMessage('status', '方案已拒绝。', { result })
  })
}

watch(() => gameStore.currentGameId, () => {
  sessionId.value = 0
  messages.value = []
  if (gameStore.currentGameId || props.global) ensureSession()
})

onMounted(ensureSession)
</script>
