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
    <textarea v-model="message" rows="4" :placeholder="placeholder" />
    <button type="button" class="primary" :disabled="!message.trim()" @click="send">
      <Send :size="17" />
      发送给智能体
    </button>
    <article v-if="reply" class="proposal-card">
      <h3>讨论回复</h3>
      <p>{{ reply }}</p>
    </article>
    <article v-if="proposal" class="proposal-card">
      <h3>待确认方案 #{{ proposal.proposal_id }}</h3>
      <pre>{{ JSON.stringify(proposal.proposed_actions, null, 2) }}</pre>
      <div class="button-row">
        <button type="button" class="primary" @click="apply(proposal.proposal_id)">
          <Check :size="17" />
          确认执行
        </button>
        <button type="button" @click="reject(proposal.proposal_id)">
          <X :size="17" />
          拒绝
        </button>
      </div>
    </article>
    <article v-if="lastResult" class="proposal-card">
      <h3>执行结果</h3>
      <pre>{{ JSON.stringify(lastResult, null, 2) }}</pre>
    </article>
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
  global: { type: Boolean, default: false }
})

const emit = defineEmits(['applied'])
const gameStore = useGameStore()
const ui = useUiStore()
const sessionId = ref(0)
const message = ref('')
const reply = ref('')
const proposal = ref(null)
const lastResult = ref(null)

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
  reply.value = ''
  proposal.value = null
  lastResult.value = null
  await ensureSession(true)
}

async function send() {
  if (!message.value.trim()) return
  if (!sessionId.value) await ensureSession()
  if (!sessionId.value) return
  await ui.run(async () => {
    const result = await sendManagementMessage(sessionId.value, message.value.trim(), props.scope)
    reply.value = result.reply
    proposal.value = result.requires_confirmation ? result : null
    lastResult.value = null
    message.value = ''
  })
}

async function apply(id) {
  await ui.run(async () => {
    lastResult.value = await applyProposal(id)
    proposal.value = null
    await gameStore.loadCurrentGame()
    emit('applied')
  })
}

async function reject(id) {
  await ui.run(async () => {
    lastResult.value = await rejectProposal(id)
    proposal.value = null
  })
}

watch(() => gameStore.currentGameId, () => {
  sessionId.value = 0
  reply.value = ''
  proposal.value = null
  lastResult.value = null
  if (gameStore.currentGameId || props.global) ensureSession()
})

onMounted(ensureSession)
</script>
