<template>
  <section ref="logRef" :class="['story-log', `story-log-${mode}`]">
    <article v-for="entry in entries" :key="entry.id || entry.turn_number" class="story-entry">
      <header class="story-entry-header">
        <small>#{{ entry.turn_number || entry.id }}</small>
      </header>
      <div v-if="mode === 'chat'" class="chat-segments">
        <div v-if="entry.user_input" class="narration-segment player-command-segment">
          <p v-for="(part, index) in paragraphs(entry.user_input)" :key="`user-command-${entry.id}-${index}`">
            <span>玩家指令</span>{{ part }}
          </p>
        </div>
        <template v-for="(segment, index) in storySegments(displayStory(entry))" :key="`${entry.id || entry.turn_number}-${index}`">
          <div v-if="segment.type === 'role'" :class="['role-message', { 'role-message-player': isProtagonistSpeaker(segment.speaker) }]">
            <template v-if="isProtagonistSpeaker(segment.speaker)">
              <div class="message-stack">
                <span class="message-name">{{ segment.speaker }}</span>
                <div class="role-bubble">
                  <p v-for="(line, lineIndex) in segment.lines" :key="`role-${index}-${lineIndex}`">{{ line }}</p>
                </div>
              </div>
              <div class="message-avatar">
                <img v-if="avatarForSpeaker(segment.speaker)" :src="avatarForSpeaker(segment.speaker)" :alt="segment.speaker" />
                <span v-else>{{ avatarInitial(segment.speaker) }}</span>
              </div>
            </template>
            <template v-else>
              <div class="message-avatar">
                <img v-if="avatarForSpeaker(segment.speaker)" :src="avatarForSpeaker(segment.speaker)" :alt="segment.speaker" />
                <span v-else>{{ avatarInitial(segment.speaker) }}</span>
              </div>
              <div class="message-stack">
                <span class="message-name">{{ segment.speaker }}</span>
                <div class="role-bubble">
                  <p v-for="(line, lineIndex) in segment.lines" :key="`role-${index}-${lineIndex}`">{{ line }}</p>
                </div>
              </div>
            </template>
          </div>
          <div v-else class="narration-segment">
            <p v-for="(line, lineIndex) in segment.lines" :key="`narration-${index}-${lineIndex}`">{{ line }}</p>
          </div>
        </template>
      </div>
      <div v-else class="narration-body">
        <div v-if="entry.user_input" class="player-command-segment user-input">
          <p v-for="(part, index) in paragraphs(entry.user_input)" :key="`narration-user-command-${entry.id}-${index}`">
            <span>玩家指令</span>{{ part }}
          </p>
        </div>
        <p v-for="(part, index) in paragraphs(displayStory(entry))" :key="`story-${entry.id}-${index}`">{{ part }}</p>
      </div>
      <footer class="story-entry-footer">
        <button
          type="button"
          class="story-icon-button"
          title="从这里重新分支"
          aria-label="从这里重新分支"
          :disabled="actionsDisabled || !entry.turn_number"
          @click="$emit('delete-from', entry)"
        >
          <Pencil :size="14" />
        </button>
        <button
          type="button"
          class="story-icon-button"
          title="重新生成"
          aria-label="重新生成"
          :disabled="actionsDisabled || !entry.turn_number"
          @click="$emit('regenerate', entry)"
        >
          <RotateCcw :size="14" />
        </button>
      </footer>
    </article>
    <article v-if="latest" class="story-entry latest">
      <header class="story-entry-header">
        <small>最新</small>
      </header>
      <div v-if="mode === 'chat'" class="chat-segments">
        <template v-for="(segment, index) in storySegments(latest.visible_story)" :key="`latest-${index}`">
          <div v-if="segment.type === 'role'" :class="['role-message', { 'role-message-player': isProtagonistSpeaker(segment.speaker) }]">
            <template v-if="isProtagonistSpeaker(segment.speaker)">
              <div class="message-stack">
                <span class="message-name">{{ segment.speaker }}</span>
                <div class="role-bubble">
                  <p v-for="(line, lineIndex) in segment.lines" :key="`latest-role-${lineIndex}`">{{ line }}</p>
                </div>
              </div>
              <div class="message-avatar">
                <img v-if="avatarForSpeaker(segment.speaker)" :src="avatarForSpeaker(segment.speaker)" :alt="segment.speaker" />
                <span v-else>{{ avatarInitial(segment.speaker) }}</span>
              </div>
            </template>
            <template v-else>
              <div class="message-avatar">
                <img v-if="avatarForSpeaker(segment.speaker)" :src="avatarForSpeaker(segment.speaker)" :alt="segment.speaker" />
                <span v-else>{{ avatarInitial(segment.speaker) }}</span>
              </div>
              <div class="message-stack">
                <span class="message-name">{{ segment.speaker }}</span>
                <div class="role-bubble">
                  <p v-for="(line, lineIndex) in segment.lines" :key="`latest-role-${lineIndex}`">{{ line }}</p>
                </div>
              </div>
            </template>
          </div>
          <div v-else class="narration-segment">
            <p v-for="(line, lineIndex) in segment.lines" :key="`latest-narration-${lineIndex}`">{{ line }}</p>
          </div>
        </template>
      </div>
      <div v-else class="narration-body">
        <p v-for="(part, index) in paragraphs(latest.visible_story)" :key="`latest-story-${index}`">{{ part }}</p>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Pencil, RotateCcw } from 'lucide-vue-next'

const props = defineProps({
  entries: { type: Array, default: () => [] },
  latest: { type: Object, default: null },
  mode: { type: String, default: 'narration' },
  characters: { type: Array, default: () => [] },
  protagonistName: { type: String, default: '你' },
  actionsDisabled: { type: Boolean, default: false }
})

defineEmits(['delete-from', 'regenerate'])

const apiBase = (import.meta.env.VITE_API_ORIGIN || 'http://localhost:8000').replace(/\/api$/, '')
const logRef = ref(null)

const characterNames = computed(() =>
  props.characters
    .map((item) => item?.name)
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
)

watch(
  () => [props.entries.length, props.latest?.visible_story],
  async () => {
    await nextTick()
    if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight
  },
  { flush: 'post' }
)

function displayStory(entry) {
  return entry?.ai_response || entry?.visible_story || ''
}

function paragraphs(text) {
  return String(text || '')
    .replace(/\r/g, '')
    .split(/\n+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .flatMap(splitLongParagraph)
}

function splitLongParagraph(part) {
  if (part.length <= 110) return [part]
  const sentences = part.match(/[^。！？!?；;]+[。！？!?；;]?/g) || [part]
  const result = []
  let buffer = ''

  for (const sentence of sentences) {
    const next = `${buffer}${sentence}`
    if (buffer && next.length > 110) {
      result.push(buffer)
      buffer = sentence
    } else {
      buffer = next
    }
  }

  if (buffer) result.push(buffer)
  return result
}

function storySegments(text) {
  const segments = []
  for (const part of paragraphs(text)) {
    const roleSegment = parseRoleSegment(part)
    pushSegment(segments, roleSegment || { type: 'narration', lines: [part] })
  }
  return segments
}

function parseRoleSegment(part) {
  if (/^[\[【（(]/u.test(part)) return null

  const explicit = part.match(/^([\u4e00-\u9fa5A-Za-z0-9_·・]{1,14})(?:\s*[（(][^）)]*[）)])?\s*[：:]\s*(.+)$/)
  if (explicit) {
    const speaker = normalizeSpeaker(explicit[1])
    if (isLikelySpeaker(speaker)) return { type: 'role', speaker, lines: [explicit[2].trim()] }
  }

  return null
}

function normalizeSpeaker(speaker) {
  return speaker.replace(/(轻声|低声)?(说道|说|问|喊|答道|道)$/u, '').trim()
}

function isLikelySpeaker(speaker) {
  if (!speaker) return false
  if (speaker.includes('无法') || speaker.includes('失败') || speaker.includes('错误')) return false
  if (speaker.includes('剧情') || speaker.includes('request')) return false
  return !/[，,。！？!?；;\s]/.test(speaker)
}

function pushSegment(segments, segment) {
  if (segment.type === 'role') {
    segments.push(segment)
    return
  }

  const last = segments[segments.length - 1]
  if (last && last.type === segment.type && last.speaker === segment.speaker) {
    last.lines.push(...segment.lines)
    return
  }
  segments.push(segment)
}

function characterForSpeaker(speaker) {
  const normalized = speaker === '你' ? props.protagonistName : speaker
  return props.characters.find((item) => item?.name === normalized) ||
    props.characters.find((item) => item?.role_type === 'protagonist' && isProtagonistSpeaker(speaker))
}

function avatarForSpeaker(speaker) {
  const avatarUrl = characterForSpeaker(speaker)?.avatar_url
  if (!avatarUrl) return ''
  return avatarUrl.startsWith('http') ? avatarUrl : `${apiBase}${avatarUrl}`
}

function avatarInitial(speaker) {
  return String(speaker || '你').trim().slice(0, 1) || '你'
}

function isProtagonistSpeaker(speaker) {
  return speaker === '你' || speaker === props.protagonistName
}
</script>
