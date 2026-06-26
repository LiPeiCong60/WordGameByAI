<template>
  <SaveContextBar @changed="loadAll" />
  <NoGamePrompt v-if="!gameStore.currentGameId" />
  <section v-else class="view-grid play-grid" :style="playGridStyle">
    <div class="panel story-panel">
      <header class="panel-header">
        <h1>{{ gameStore.currentGame?.title || '未选择游戏' }}</h1>
        <button type="button" class="icon-button" title="刷新" @click="loadAll"><RefreshCw :size="17" /></button>
      </header>
      <div class="scene-toolbar">
        <div class="scene-meta" aria-label="当前场景信息">
          <span><Clock3 :size="15" />时间<strong>{{ sceneTime }}</strong></span>
          <span><MapPin :size="15" />地点<strong>{{ sceneLocation }}</strong></span>
          <span><Globe2 :size="15" />世界<strong>{{ sceneWorld }}</strong></span>
          <span>状态<strong>{{ sceneStatus }}</strong></span>
        </div>
        <div class="mode-switch" role="tablist" aria-label="剧情显示方式">
          <button
            type="button"
            :class="{ active: storyMode === 'narration' }"
            title="旁白模式"
            @click="setStoryMode('narration')"
          >
            <BookOpen :size="15" />
            旁白
          </button>
          <button
            type="button"
            :class="{ active: storyMode === 'chat' }"
            title="聊天框模式"
            @click="setStoryMode('chat')"
          >
            <MessageSquare :size="15" />
            聊天框
          </button>
        </div>
      </div>
      <StoryLog
        :entries="turnLogs"
        :latest="latestTurn"
        :mode="storyMode"
        :characters="characters"
        :protagonist-name="protagonist?.name || '你'"
        @delete-from="deleteFromEntry"
        @regenerate="regenerateEntry"
      />
      <div v-if="streamStatus" class="stream-status">{{ streamStatus }}</div>
      <form class="turn-box" @submit.prevent="submitTurn">
        <textarea v-model="userInput" rows="4" placeholder="输入玩家行动" :disabled="isStreaming" />
        <button type="submit" class="primary" :disabled="isStreaming">
          <Send :size="17" />
          {{ isStreaming ? '生成中...' : '推进剧情' }}
        </button>
      </form>
      <div v-if="checkerIssues.length" class="warning-box">
        <strong>CheckerAgent 警告</strong>
        <p v-for="issue in checkerIssues" :key="issue.message">{{ issue.message }}</p>
      </div>
    </div>

    <div
      class="rail-resizer"
      role="separator"
      aria-label="调整右侧状态栏宽度"
      aria-orientation="vertical"
      tabindex="0"
      @pointerdown="startRailResize"
      @keydown.left.prevent="adjustRightRail(32)"
      @keydown.right.prevent="adjustRightRail(-32)"
    />

    <aside class="right-rail">
      <div class="right-rail-fixed">
        <section class="panel">
          <header class="panel-header"><h2>当前状态</h2></header>
          <dl class="info-list">
            <div><dt>题材</dt><dd>{{ gameStore.currentGame?.genre || '-' }}</dd></div>
            <div><dt>世界</dt><dd>{{ gameStore.currentWorld?.name || '-' }}</dd></div>
            <div><dt>状态</dt><dd>{{ gameStore.currentGame?.current_state || '-' }}</dd></div>
          </dl>
        </section>
        <CharacterCard v-if="protagonist" :character="protagonist" />
        <section v-else class="panel">
          <header class="panel-header"><h2>主角状态</h2></header>
          <p class="muted-text">还没有创建主角。请到“角色”页新增一个角色类型为“主角”的角色。</p>
        </section>
        <InventoryPanel title="主角背包" :records="protagonistInventory" :items="items" />
      </div>
      <div class="right-rail-scroll">
        <NpcStatusPanel :npcs="npcs" collapsible />
        <InventoryPanel title="队伍公共物资" :records="partyInventory" :items="items" collapsible />
        <details class="panel collapsible-panel" open>
          <summary class="panel-header collapsible-summary">
            <h2>重要事件</h2>
            <span>{{ events.slice(0, 5).length }}</span>
            <ChevronDown class="collapsible-icon" :size="17" />
          </summary>
          <div class="collapsible-content">
            <EventList :events="events.slice(0, 5)" />
          </div>
        </details>
      </div>
    </aside>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpen, ChevronDown, Clock3, Globe2, MapPin, MessageSquare, RefreshCw, Send } from 'lucide-vue-next'
import CharacterCard from '../components/CharacterCard.vue'
import EventList from '../components/EventList.vue'
import InventoryPanel from '../components/InventoryPanel.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import NpcStatusPanel from '../components/NpcStatusPanel.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import StoryLog from '../components/StoryLog.vue'
import { listCharacters } from '../api/characters'
import { listEvents } from '../api/events'
import { exportGame } from '../api/games'
import { listInventory } from '../api/inventory'
import { listItems } from '../api/items'
import { deleteTurnsFrom, regenerateTurnStream, runOpeningStream, runTurnStream } from '../api/turns'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { ensureStarterCharacters } from '../utils/starterCharacters'

const route = useRoute()
const gameStore = useGameStore()
const ui = useUiStore()
const characters = ref([])
const items = ref([])
const inventory = ref([])
const events = ref([])
const turnLogs = ref([])
const latestTurn = ref(null)
const userInput = ref('')
const isStreaming = ref(false)
const streamStatus = ref('')
const storyMode = ref(localStorage.getItem('storyDisplayMode') || 'chat')
const rightRailWidth = ref(Number(localStorage.getItem('playRightRailWidth')) || 460)

const protagonist = computed(() => characters.value.find((item) => item.role_type === 'protagonist'))
const npcs = computed(() => characters.value.filter((item) => item.role_type !== 'protagonist'))
const protagonistInventory = computed(() => inventory.value.filter((row) => row.owner_type === 'character' && row.owner_id === protagonist.value?.id))
const partyInventory = computed(() => inventory.value.filter((row) => row.owner_type === 'party'))
const checkerIssues = computed(() => latestTurn.value?.checker_result?.issues || [])
const sceneTime = computed(() => {
  const value = extractLabeledValue([gameStore.currentGame?.current_state, gameStore.currentWorld?.current_status], ['当前时间', '时间', '日期'])
  return value || '未记录'
})
const sceneLocation = computed(() =>
  protagonist.value?.current_location ||
  extractLabeledValue([gameStore.currentWorld?.current_status, gameStore.currentGame?.current_state], ['当前位置', '地点', '位置']) ||
  '未记录'
)
const sceneWorld = computed(() => gameStore.currentWorld?.name || gameStore.currentGame?.world_type || '未设置')
const sceneStatus = computed(() => summarizeSceneStatus(gameStore.currentGame?.current_state || gameStore.currentWorld?.current_status || '进行中'))
const playGridStyle = computed(() => ({ '--right-rail-width': `${rightRailWidth.value}px` }))

async function ensureGame() {
  const routeGameId = Number(route.params.gameId)
  const id = routeGameId || gameStore.currentGameId
  if (id) await gameStore.loadCurrentGame(id)
}

async function loadAll(options = {}) {
  const autoOpening = options.autoOpening !== false
  let shouldGenerateOpening = false
  await ui.run(async () => {
    await ensureGame()
    if (!gameStore.currentGameId) return
    const gameId = gameStore.currentGameId
    const starterResult = await ensureStarterCharacters(gameId, gameStore.currentGame)
    characters.value = starterResult.created ? await listCharacters(gameId) : starterResult.characters
    items.value = await listItems(gameId)
    inventory.value = await listInventory(gameId)
    events.value = await listEvents(gameId)
    const save = await exportGame(gameId)
    const logs = save.turn_logs || []
    turnLogs.value = logs.slice(-8)
    if (!isStreaming.value) latestTurn.value = null
    shouldGenerateOpening = autoOpening && logs.length === 0 && !isStreaming.value
  })
  if (shouldGenerateOpening) await generateOpening()
}

function setStoryMode(mode) {
  storyMode.value = mode
  localStorage.setItem('storyDisplayMode', mode)
}

function extractLabeledValue(sources, labels) {
  for (const source of sources.filter(Boolean)) {
    for (const label of labels) {
      const match = String(source).match(new RegExp(`${label}\\s*[：:]\\s*([^，。；;\\n]+)`))
      if (match?.[1]) return match[1].trim()
    }
  }
  return ''
}

function summarizeSceneStatus(text) {
  const value = String(text || '').trim()
  if (!value || value === '-') return '进行中'
  return value.length > 18 ? `${value.slice(0, 18)}...` : value
}

function startRailResize(event) {
  if (window.innerWidth <= 980) return
  event.preventDefault()
  const startX = event.clientX
  const startWidth = rightRailWidth.value

  document.body.classList.add('is-resizing-rail')
  const move = (moveEvent) => {
    setRightRailWidth(startWidth + startX - moveEvent.clientX)
  }
  const stop = () => {
    document.body.classList.remove('is-resizing-rail')
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', stop)
  }

  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', stop)
}

function adjustRightRail(delta) {
  setRightRailWidth(rightRailWidth.value + delta)
}

function setRightRailWidth(value) {
  rightRailWidth.value = clampRightRailWidth(value)
  localStorage.setItem('playRightRailWidth', String(rightRailWidth.value))
}

function clampRightRailWidth(value) {
  if (window.innerWidth <= 980) return 460
  const sidebarWidth = 236
  const available = window.innerWidth - sidebarWidth - 72
  const maxWidth = Math.max(300, Math.min(780, available - 360))
  return Math.round(Math.min(Math.max(value, 300), maxWidth))
}

async function submitTurn() {
  if (!userInput.value.trim() || !gameStore.currentGameId) return
  const action = userInput.value.trim()
  userInput.value = ''
  await streamTurn(async (onEvent) => runTurnStream(gameStore.currentGameId, action, onEvent))
}

async function generateOpening() {
  if (!gameStore.currentGameId || isStreaming.value) return
  await streamTurn(
    async (onEvent) => runOpeningStream(gameStore.currentGameId, onEvent),
    { opening: true }
  )
}

function handleStreamEvent(event) {
  if (event.type === 'status') {
    streamStatus.value = event.message
    return
  }
  if (event.type === 'delta') {
    if (!latestTurn.value) latestTurn.value = { visible_story: '', checker_result: { ok: true, issues: [] } }
    latestTurn.value.visible_story += event.text
    return
  }
  if (event.type === 'done') {
    latestTurn.value = event
    streamStatus.value = '生成完成'
    return
  }
  if (event.type === 'error') {
    throw new Error(event.message)
  }
}

async function streamTurn(runner, options = {}) {
  isStreaming.value = true
  streamStatus.value = options.opening ? '正在生成开场白...' : '正在连接模型...'
  latestTurn.value = { visible_story: '', checker_result: { ok: true, issues: [] } }
  ui.clearError()
  try {
    await runner(handleStreamEvent)
    await loadAll({ autoOpening: false })
    latestTurn.value = null
  } catch (error) {
    ui.setError(error)
    latestTurn.value = {
      visible_story: `无法生成剧情：${error?.message || '流式生成失败'}`,
      checker_result: { ok: false, issues: [{ message: error?.message || '流式生成失败' }] }
    }
  } finally {
    isStreaming.value = false
    setTimeout(() => {
      if (!isStreaming.value) streamStatus.value = ''
    }, 1200)
  }
}

async function deleteFromEntry(entry) {
  const turnId = entry.id || entry.turn_id
  if (!turnId) return
  if (!window.confirm('确定删除这一轮及之后的剧情吗？如果这轮有快照，系统会回到这一轮之前。')) return
  await ui.run(async () => {
    await deleteTurnsFrom(turnId)
    latestTurn.value = null
    await gameStore.loadCurrentGame()
    await loadAll()
  })
}

async function regenerateEntry(entry) {
  const turnId = entry.id || entry.turn_id
  if (!turnId) return
  if (!window.confirm('确定重新生成这一轮吗？系统会先回到这一轮之前，再用同一句玩家行动重新推进。')) return
  await streamTurn(async (onEvent) => {
    await regenerateTurnStream(turnId, onEvent)
    await gameStore.loadCurrentGame()
  })
}

onMounted(() => {
  rightRailWidth.value = clampRightRailWidth(rightRailWidth.value)
  loadAll()
})
</script>
