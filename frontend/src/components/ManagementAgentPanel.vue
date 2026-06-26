<template>
  <section class="panel management-panel">
    <header class="panel-header">
      <h2>存档管理智能体</h2>
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
    <textarea :value="message" rows="4" placeholder="描述你想调整的存档、角色、物品、库存、世界、设定、事件或状态" @input="$emit('update:message', $event.target.value)" />
    <button type="button" class="primary" @click="$emit('send')">
      <Send :size="17" />
      发送
    </button>
    <article v-if="reply" class="proposal-card">
      <h3>回复</h3>
      <p>{{ reply }}</p>
    </article>
    <article v-if="proposal" class="proposal-card">
      <h3>修改方案 #{{ proposal.proposal_id }}</h3>
      <pre>{{ JSON.stringify(proposal.proposed_actions, null, 2) }}</pre>
      <div class="button-row">
        <button type="button" class="primary" @click="$emit('apply', proposal.proposal_id)">
          <Check :size="17" />
          确认执行
        </button>
        <button type="button" @click="$emit('reject', proposal.proposal_id)">
          <X :size="17" />
          拒绝
        </button>
      </div>
    </article>
  </section>
</template>

<script setup>
import { Check, Plus, Send, X } from 'lucide-vue-next'

defineProps({
  sessions: { type: Array, default: () => [] },
  scopes: { type: Array, default: () => [{ value: '综合管理', label: '综合管理' }] },
  scope: { type: String, default: '综合管理' },
  sessionId: { type: Number, default: 0 },
  message: { type: String, default: '' },
  reply: { type: String, default: '' },
  proposal: { type: Object, default: null }
})

defineEmits(['create-session', 'update:sessionId', 'update:scope', 'update:message', 'send', 'apply', 'reject'])
</script>
