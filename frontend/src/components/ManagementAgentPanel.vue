<template>
  <section class="panel management-panel">
    <header class="panel-header">
      <div class="agent-heading"><span class="agent-mark"><Bot :size="20" /></span><div><h2>存档管理智能体</h2><small>World Game AI 助手</small></div></div>
      <button type="button" class="icon-button" title="新建会话" @click="$emit('create-session')">
        <Plus :size="17" />
      </button>
    </header>
    <div class="notice">
      <p>一个智能体统一管理当前存档。它会先给出修改方案，确认后才会写入数据。</p>
    </div>
    <div class="agent-controls">
      <select :value="sessionId" @change="$emit('update:sessionId', Number($event.target.value))">
        <option :value="0">选择会话</option>
        <option v-for="session in sessions" :key="session.id" :value="session.id">{{ session.title }} #{{ session.id }}</option>
      </select>
      <select :value="scope" @change="$emit('update:scope', $event.target.value)">
        <option v-for="option in scopes" :key="option.value" :value="option.value">{{ option.label }}</option>
      </select>
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
            <h3>修改方案 #{{ item.proposal.proposal_id }}</h3>
            <pre>{{ JSON.stringify(item.proposal.proposed_actions, null, 2) }}</pre>
            <div class="button-row">
              <button type="button" class="primary" @click="$emit('apply', item.proposal.proposal_id)">
                <Check :size="17" />
                确认执行
              </button>
              <button type="button" @click="$emit('reject', item.proposal.proposal_id)">
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
          <p class="typing-indicator"><i></i><i></i><i></i><span>正在整理回复</span></p>
        </div>
      </article>
    </div>
    <form class="agent-composer" @submit.prevent="$emit('send')">
      <textarea :value="message" rows="4" placeholder="描述你想调整的存档、角色、世界、设定或状态" @input="$emit('update:message', $event.target.value)" />
      <button type="submit" class="primary" :disabled="!message.trim() || pending">
        <Send :size="17" />
        发送
      </button>
    </form>
  </section>
</template>

<script setup>
import { Bot, Check, Plus, Send, X } from 'lucide-vue-next'

defineProps({
  sessions: { type: Array, default: () => [] },
  scopes: { type: Array, default: () => [{ value: '综合管理', label: '综合管理' }] },
  scope: { type: String, default: '综合管理' },
  sessionId: { type: Number, default: 0 },
  message: { type: String, default: '' },
  messages: { type: Array, default: () => [] },
  pending: { type: Boolean, default: false }
})

defineEmits(['create-session', 'update:sessionId', 'update:scope', 'update:message', 'send', 'apply', 'reject'])

function roleLabel(role) {
  if (role === 'user') return '你'
  if (role === 'status') return '状态'
  return '智能体'
}
</script>
