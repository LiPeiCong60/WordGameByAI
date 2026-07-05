<template>
  <article class="character-card">
    <img v-if="avatarSrc" class="avatar" :src="avatarSrc" :alt="character.name" @error="imageFailed = true" />
    <div v-else class="avatar-fallback" aria-hidden="true">{{ initials }}</div>
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
        <div><dt>好感</dt><dd>{{ character.affection_score ?? 0 }}</dd></div>
        <div><dt>信任</dt><dd>{{ character.trust_score ?? 0 }}</dd></div>
        <div><dt>张力</dt><dd>{{ character.tension_score ?? 0 }}</dd></div>
      </dl>
      <p v-if="character.abilities">{{ character.abilities }}</p>
    </div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { characterStatusLabels, labelFor, roleTypeLabels } from '../utils/labels'

const props = defineProps({
  character: { type: Object, required: true }
})

const imageFailed = ref(false)
const apiBase = (import.meta.env.VITE_API_ORIGIN || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/api$/, '')
const avatarSrc = computed(() => {
  if (imageFailed.value || !props.character.avatar_url) return ''
  return `${apiBase}${props.character.avatar_url}`
})
const initials = computed(() => String(props.character.name || '?').slice(0, 1))

watch(
  () => props.character.avatar_url,
  () => {
    imageFailed.value = false
  }
)
</script>
