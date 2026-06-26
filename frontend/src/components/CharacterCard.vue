<template>
  <article class="character-card">
    <img class="avatar" :src="avatarSrc" :alt="character.name" />
    <div class="card-body">
      <header>
        <h3>{{ character.name || '未命名角色' }}</h3>
        <span class="pill">{{ labelFor(roleTypeLabels, character.role_type) }}</span>
      </header>
      <dl>
        <div><dt>状态</dt><dd>{{ labelFor(characterStatusLabels, character.status) }}</dd></div>
        <div><dt>心情</dt><dd>{{ character.mood || '-' }}</dd></div>
        <div><dt>位置</dt><dd>{{ character.current_location || '-' }}</dd></div>
        <div><dt>关系</dt><dd>{{ character.relationship_to_player || '-' }} · {{ character.relationship_score ?? 0 }}</dd></div>
      </dl>
      <p v-if="character.abilities">{{ character.abilities }}</p>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { characterStatusLabels, labelFor, roleTypeLabels } from '../utils/labels'

const props = defineProps({
  character: { type: Object, required: true }
})

const apiBase = (import.meta.env.VITE_API_ORIGIN || 'http://localhost:8000').replace(/\/api$/, '')
const avatarSrc = computed(() => props.character.avatar_url ? `${apiBase}${props.character.avatar_url}` : `${apiBase}/uploads/characters/placeholder.png`)
</script>
