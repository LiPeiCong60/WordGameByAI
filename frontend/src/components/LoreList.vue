<template>
  <div class="stack-list">
    <article v-for="lore in loreItems" :key="lore.id" class="list-card">
      <header>
        <h3>{{ lore.title }}</h3>
        <span class="pill">{{ labelFor(canonLevelLabels, lore.canon_level) }}</span>
      </header>
      <p>{{ lore.content }}</p>
      <footer>{{ lore.category }} · 重要度 {{ lore.importance }}</footer>
      <div v-if="$slots.actions" class="button-row">
        <slot name="actions" :lore="lore" />
      </div>
    </article>
  </div>
</template>

<script setup>
import { canonLevelLabels, labelFor } from '../utils/labels'

defineProps({
  loreItems: { type: Array, default: () => [] }
})
</script>
