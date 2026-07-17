<template>
  <span
    class="character-avatar"
    :class="`character-avatar--${normalizedShape}`"
    :style="avatarStyle"
    role="img"
    :aria-label="accessibleLabel"
    :title="accessibleLabel"
  >
    <img
      v-if="!fallbackFailed"
      class="character-avatar__image"
      :src="displayedSrc"
      :alt="accessibleLabel"
      :loading="loading"
      :decoding="decoding"
      @error="handleImageError"
    />
    <span v-else class="character-avatar__initial" aria-hidden="true">{{ initial }}</span>
    <span
      v-if="showAutoBadge && isUsingDefault"
      class="character-avatar__badge"
      aria-label="智能匹配头像"
      title="智能匹配头像"
    >✦</span>
  </span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { matchDefaultAvatar } from '../utils/defaultAvatars'

const props = defineProps({
  character: { type: Object, default: () => ({}) },
  avatarUrl: { type: String, default: '' },
  size: { type: [Number, String], default: 44 },
  shape: {
    type: String,
    default: 'circle',
    validator: (value) => ['circle', 'rounded', 'square'].includes(value)
  },
  showAutoBadge: { type: Boolean, default: false },
  loading: { type: String, default: 'lazy' },
  decoding: { type: String, default: 'async' }
})

const emit = defineEmits(['load-error'])
const uploadedImageFailed = ref(false)
const fallbackFailed = ref(false)

function resolveApiOrigin() {
  const explicitOrigin = String(import.meta.env.VITE_API_ORIGIN || '').trim()
  if (explicitOrigin) return explicitOrigin.replace(/\/+$/, '')
  const apiBase = String(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').trim()
  try {
    return new URL(apiBase, globalThis.location?.origin || 'http://localhost:8000').origin
  } catch {
    return apiBase.replace(/\/api(?:\/v\d+)?\/?$/, '').replace(/\/+$/, '')
  }
}

const apiOrigin = resolveApiOrigin()

const profile = computed(() => matchDefaultAvatar(props.character))
const rawUploadedUrl = computed(() => String(props.avatarUrl || props.character?.avatar_url || '').trim())

const uploadedSrc = computed(() => {
  const source = rawUploadedUrl.value
  if (!source) return ''
  if (/^(?:https?:)?\/\//i.test(source) || /^(?:data|blob):/i.test(source)) return source
  if (source.startsWith('/assets/')) return source
  return `${apiOrigin}${source.startsWith('/') ? '' : '/'}${source}`
})

const isUsingDefault = computed(() => !uploadedSrc.value || uploadedImageFailed.value)
const displayedSrc = computed(() => isUsingDefault.value ? profile.value.assetPath : uploadedSrc.value)
const normalizedShape = computed(() => ['circle', 'rounded', 'square'].includes(props.shape) ? props.shape : 'circle')
const pixelSize = computed(() => Math.max(16, Number.parseFloat(props.size) || 44))
const avatarStyle = computed(() => ({
  '--avatar-size': `${pixelSize.value}px`,
  '--avatar-badge-size': `${Math.max(16, pixelSize.value * 0.34)}px`
}))
const characterName = computed(() => String(props.character?.name || '').trim())
const initial = computed(() => Array.from(characterName.value || '?')[0])
const accessibleLabel = computed(() => {
  const name = characterName.value || '角色'
  return isUsingDefault.value
    ? `${name}的头像，智能匹配为${profile.value.label}`
    : `${name}的头像`
})

function handleImageError(event) {
  if (!isUsingDefault.value) {
    uploadedImageFailed.value = true
    emit('load-error', { source: uploadedSrc.value, fallback: profile.value })
    return
  }
  fallbackFailed.value = true
  emit('load-error', { source: displayedSrc.value, fallback: null })
}

watch(
  () => [rawUploadedUrl.value, profile.value.id],
  () => {
    uploadedImageFailed.value = false
    fallbackFailed.value = false
  }
)
</script>

<style scoped>
.character-avatar {
  position: relative;
  display: inline-grid;
  flex: 0 0 var(--avatar-size);
  width: var(--avatar-size);
  height: var(--avatar-size);
  place-items: center;
  overflow: visible;
  color: #1269c7;
  vertical-align: middle;
}

.character-avatar::before {
  position: absolute;
  inset: 0;
  z-index: 1;
  border: 1.5px solid rgba(41, 91, 142, 0.2);
  border-radius: inherit;
  box-shadow: 0 4px 14px rgba(19, 90, 158, 0.14);
  content: '';
  pointer-events: none;
}

.character-avatar--circle {
  border-radius: 50%;
}

.character-avatar--rounded {
  border-radius: 24%;
}

.character-avatar--square {
  border-radius: 8%;
}

.character-avatar__image,
.character-avatar__initial {
  width: 100%;
  height: 100%;
  border-radius: inherit;
}

.character-avatar__image {
  display: block;
  object-fit: cover;
  background: linear-gradient(145deg, #e5f4ff, #fff6db);
}

.character-avatar__initial {
  display: grid;
  place-items: center;
  overflow: hidden;
  background: linear-gradient(145deg, #d9efff, #fff1bd);
  font-size: calc(var(--avatar-size) * 0.43);
  font-weight: 800;
  line-height: 1;
}

.character-avatar__badge {
  position: absolute;
  right: -3px;
  bottom: -3px;
  z-index: 2;
  display: grid;
  width: var(--avatar-badge-size);
  height: var(--avatar-badge-size);
  box-sizing: border-box;
  place-items: center;
  border: 2px solid #fff;
  border-radius: 50%;
  background: linear-gradient(145deg, #087ff5, #12b8eb);
  box-shadow: 0 2px 7px rgba(8, 102, 203, 0.28);
  color: #fff;
  font-size: calc(var(--avatar-badge-size) * 0.62);
  line-height: 1;
}
</style>
