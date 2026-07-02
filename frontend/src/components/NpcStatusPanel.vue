<template>
  <section v-if="collapsible" class="panel collapsible-panel" :class="{ open: isOpen }">
    <button type="button" class="panel-header collapsible-summary" :aria-expanded="isOpen" @click="isOpen = !isOpen">
      <h2>NPC 状态</h2>
      <span>{{ npcs.length }}</span>
      <ChevronDown class="collapsible-icon" :class="{ open: isOpen }" :size="17" />
    </button>
    <div v-show="isOpen" class="npc-grid">
      <CharacterCard v-for="npc in npcs" :key="npc.id" :character="npc" />
    </div>
  </section>
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
import { ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import CharacterCard from './CharacterCard.vue'

const props = defineProps({
  npcs: { type: Array, default: () => [] },
  collapsible: { type: Boolean, default: false },
  defaultOpen: { type: Boolean, default: true }
})

const isOpen = ref(props.defaultOpen)
</script>
