<template>
  <details v-if="collapsible" class="panel collapsible-panel" open>
    <summary class="panel-header collapsible-summary">
      <h2>NPC 状态</h2>
      <span>{{ npcs.length }}</span>
      <ChevronDown class="collapsible-icon" :size="17" />
    </summary>
    <div class="npc-grid">
      <CharacterCard v-for="npc in npcs" :key="npc.id" :character="npc" />
    </div>
  </details>
  <section v-else class="panel">
    <header class="panel-header">
      <h2>NPC 状态</h2>
      <span>{{ npcs.length }}</span>
    </header>
    <div class="npc-grid">
      <CharacterCard v-for="npc in npcs" :key="npc.id" :character="npc" />
    </div>
  </section>
</template>

<script setup>
import { ChevronDown } from 'lucide-vue-next'
import CharacterCard from './CharacterCard.vue'

defineProps({
  npcs: { type: Array, default: () => [] },
  collapsible: { type: Boolean, default: false }
})
</script>
