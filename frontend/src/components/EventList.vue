<template>
  <div class="stack-list">
    <article v-for="event in events" :key="event.id" class="list-card">
      <header>
        <h3>{{ event.title }}</h3>
        <span class="pill">{{ labelFor(eventStatusLabels, event.status) }}</span>
      </header>
      <p>{{ event.summary || event.consequence }}</p>
      <footer>{{ event.event_type }} · {{ event.arc_name || '未分章' }} · 重要度 {{ event.importance }}</footer>
      <div v-if="$slots.actions" class="button-row">
        <slot name="actions" :event="event" />
      </div>
    </article>
  </div>
</template>

<script setup>
import { eventStatusLabels, labelFor } from '../utils/labels'

defineProps({
  events: { type: Array, default: () => [] }
})
</script>
