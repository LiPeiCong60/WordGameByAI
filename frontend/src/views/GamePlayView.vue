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
        <div class="mode-switch speed-switch" role="tablist" aria-label="生成速度">
          <button
            type="button"
            :class="{ active: generationMode === 'instant' }"
            title="极速模式：跳过前置角色推演和完整状态整理，只应用 Hint 即时更新角色软状态"
            @click="setGenerationMode('instant')"
          >
            <Zap :size="15" />
            极速
          </button>
          <button
            type="button"
            :class="{ active: generationMode === 'fast' }"
            title="快速模式：跳过前置主角/NPC 独立推演，剧情先返回，状态在后台完整整理"
            @click="setGenerationMode('fast')"
          >
            <Gauge :size="15" />
            快速
          </button>
          <button
            type="button"
            :class="{ active: generationMode === 'full' }"
            title="精细模式：完整执行主角 Agent 和 NPC Agent，质量更稳但更慢"
            @click="setGenerationMode('full')"
          >
            <SlidersHorizontal :size="15" />
            精细
          </button>
        </div>
      </div>
      <StoryLog
        :entries="turnLogs"
        :latest="latestTurn"
        :mode="storyMode"
        :characters="characters"
        :protagonist-name="protagonist?.name || '你'"
        :actions-disabled="isStreaming || stateSyncPending || stateSyncPolling"
        @delete-from="deleteFromEntry"
        @regenerate="regenerateEntry"
      />
      <div v-if="streamStatus" class="stream-status">{{ streamStatus }}</div>
      <div v-if="stateSyncPending" class="stream-status state-sync-status">状态同步中，完成后会自动刷新角色状态...</div>
      <form class="turn-box" @submit.prevent="submitTurn">
        <div v-if="branchEditTarget" class="branch-edit-banner">
          <span>正在编辑第 {{ branchEditTarget.turn_number }} 轮输入，提交后会从这一轮重新分支。</span>
          <button type="button" @click="clearBranchEdit">取消</button>
        </div>
        <div class="turn-input-grid">
          <label class="turn-field">
            <span>行动 / 背景 / 希望响应</span>
            <textarea
              ref="actionInputRef"
              v-model="actionInput"
              rows="3"
              placeholder="例如：带杯热可可下楼，观察她的反应，希望气氛自然一点"
              :disabled="isStreaming"
            />
          </label>
          <label class="turn-field">
            <span>角色说的话</span>
            <textarea
              v-model="dialogueInput"
              rows="2"
              placeholder="例如：今天怎么想起我了，大忙人"
              :disabled="isStreaming"
            />
          </label>
        </div>
        <label class="turn-option">
          <input v-model="autoCompleteBlank" type="checkbox" :disabled="isStreaming" />
          <span>空白项交给系统根据上下文补全</span>
        </label>
        <button type="submit" class="primary" :disabled="isStreaming || queuedTurnPayload || !canSubmitTurn">
          <Send :size="17" />
          {{ submitButtonText }}
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
      </div>
      <div class="right-rail-scroll">
        <NpcStatusPanel :npcs="npcs" collapsible />
      </div>
    </aside>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpen, Clock3, Gauge, Globe2, MapPin, MessageSquare, RefreshCw, Send, SlidersHorizontal, Zap } from 'lucide-vue-next'
import CharacterCard from '../components/CharacterCard.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import NpcStatusPanel from '../components/NpcStatusPanel.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import StoryLog from '../components/StoryLog.vue'
import { listCharacters } from '../api/characters'
import { exportGame } from '../api/games'
import { deleteTurnsFrom, regenerateTurnStream, runOpeningStream, runTurnStream } from '../api/turns'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { ensureStarterCharacters } from '../utils/starterCharacters'

const route = useRoute()
const gameStore = useGameStore()
const ui = useUiStore()
const characters = ref([])
const turnLogs = ref([])
const latestTurn = ref(null)
const actionInput = ref('')
const actionInputRef = ref(null)
const dialogueInput = ref('')
const autoCompleteBlank = ref(localStorage.getItem('autoCompleteTurnBlank') !== 'false')
const branchEditTarget = ref(null)
const isStreaming = ref(false)
const streamStatus = ref('')
const stateSyncPending = ref(false)
const stateSyncPolling = ref(false)
const queuedTurnPayload = ref(null)
const storyMode = ref(localStorage.getItem('storyDisplayMode') || 'chat')
const generationMode = ref(localStorage.getItem('generationMode') || 'fast')
const rightRailWidth = ref(Number(localStorage.getItem('playRightRailWidth')) || 460)

const protagonist = computed(() => characters.value.find((item) => item.role_type === 'protagonist'))
const npcs = computed(() => characters.value.filter((item) => item.role_type !== 'protagonist'))
const checkerIssues = computed(() => latestTurn.value?.checker_result?.issues || [])
const canSubmitTurn = computed(() => Boolean(actionInput.value.trim() || dialogueInput.value.trim()))
const submitButtonText = computed(() => {
  if (isStreaming.value) return '生成中...'
  if (queuedTurnPayload.value) return '已排队'
  if (stateSyncPending.value) return '同步后推进'
  if (branchEditTarget.value) return '重新分支'
  return '推进剧情'
})
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
    if (!gameStore.currentGameId) {
      stateSyncPending.value = false
      return
    }
    const gameId = gameStore.currentGameId
    const starterResult = await ensureStarterCharacters(gameId, gameStore.currentGame)
    characters.value = starterResult.created ? await listCharacters(gameId) : starterResult.characters
    const save = await exportGame(gameId)
    const logs = (save.turn_logs || []).map(normalizeTurnLog)
    turnLogs.value = logs.slice(-8)
    stateSyncPending.value = logs.some(isStateSyncPending)
    if (!isStreaming.value) latestTurn.value = null
    shouldGenerateOpening = autoOpening && logs.length === 0 && !isStreaming.value
  })
  if (shouldGenerateOpening) await generateOpening()
}

function setStoryMode(mode) {
  storyMode.value = mode
  localStorage.setItem('storyDisplayMode', mode)
}

function setGenerationMode(mode) {
  generationMode.value = mode
  localStorage.setItem('generationMode', mode)
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
  if (!canSubmitTurn.value || !gameStore.currentGameId) return
  const payload = buildTurnPayload()
  const branchTarget = branchEditTarget.value ? { ...branchEditTarget.value } : null
  actionInput.value = ''
  dialogueInput.value = ''
  branchEditTarget.value = null
  localStorage.setItem('autoCompleteTurnBlank', String(autoCompleteBlank.value))
  if (stateSyncPending.value) {
    queuedTurnPayload.value = { payload, branchTarget }
    streamStatus.value = '行动已排队，状态同步完成后自动推进...'
    startStateSyncPolling()
    return
  }
  await runSubmittedTurn(payload, branchTarget)
}

async function runSubmittedTurn(payload, branchTarget = null) {
  await streamTurn(async (onEvent) => {
    if (branchTarget) {
      onEvent({ type: 'status', message: `正在回到第 ${branchTarget.turn_number} 轮之前...` })
      await deleteTurnsFrom(branchTarget.turn_id, {
        game_id: branchTarget.game_id,
        turn_number: branchTarget.turn_number
      })
      await gameStore.loadCurrentGame()
    }
    return runTurnStream(
      gameStore.currentGameId,
      payload,
      onEvent,
      {
        fast_mode: generationMode.value !== 'full',
        skip_state_update: generationMode.value === 'instant',
        async_state_update: generationMode.value === 'fast'
      }
    )
  })
}

function buildTurnPayload() {
  const action = actionInput.value.trim()
  const dialogue = dialogueInput.value.trim()
  return {
    user_input: formatTurnInput(action, dialogue, autoCompleteBlank.value),
    action_input: action,
    dialogue_input: dialogue,
    auto_complete_blank: autoCompleteBlank.value
  }
}

function formatTurnInput(action, dialogue, autoComplete) {
  const lines = []
  if (action) lines.push(`行动：${action}`)
  if (dialogue) lines.push(`台词：${dialogue}`)
  if (!action || !dialogue) lines.push(`空白补全：${autoComplete ? '开启' : '关闭'}`)
  return lines.join('\n')
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
    stateSyncPending.value = Boolean(event.async_state_update || event.checker_result?.pending)
    streamStatus.value = stateSyncPending.value ? '剧情已完成，状态后台同步中...' : '生成完成'
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
    if (stateSyncPending.value) {
      startStateSyncPolling()
    }
  } catch (error) {
    ui.setError(error)
    latestTurn.value = {
      visible_story: `无法生成剧情：${error?.message || '流式生成失败'}`,
      checker_result: { ok: false, issues: [{ message: error?.message || '流式生成失败' }] }
    }
  } finally {
    isStreaming.value = false
    setTimeout(() => {
      if (!isStreaming.value && !stateSyncPending.value && !stateSyncPolling.value && !queuedTurnPayload.value) streamStatus.value = ''
    }, 1200)
  }
}

function parseJsonField(value, fallback) {
  if (value && typeof value === 'object') return value
  if (typeof value !== 'string' || !value.trim()) return fallback
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

function normalizeTurnLog(entry) {
  return {
    ...entry,
    npc_reactions: parseJsonField(entry.npc_reactions, {}),
    state_patch: parseJsonField(entry.state_patch, {}),
    checker_result: parseJsonField(entry.checker_result, {})
  }
}

function isStateSyncPending(entry) {
  return Boolean(entry?.checker_result?.pending)
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function startStateSyncPolling() {
  if (!stateSyncPolling.value) {
    void pollStateSync()
  }
}

async function pollStateSync() {
  if (stateSyncPolling.value) return
  stateSyncPolling.value = true
  let queuedPayload = null
  streamStatus.value = '剧情已完成，状态后台同步中...'
  try {
    for (let index = 0; index < 40; index += 1) {
      await sleep(1500)
      if (!gameStore.currentGameId) return
      await gameStore.loadCurrentGame()
      await loadAll({ autoOpening: false })
      if (!stateSyncPending.value) {
        queuedPayload = queuedTurnPayload.value
        queuedTurnPayload.value = null
        streamStatus.value = queuedPayload ? '状态已同步，正在推进排队行动...' : '状态已同步'
        break
      }
    }
    if (stateSyncPending.value) {
      streamStatus.value = '状态仍在后台同步，可稍后刷新查看'
    }
  } finally {
    stateSyncPolling.value = false
  }

  if (queuedPayload && gameStore.currentGameId) {
    await runSubmittedTurn(queuedPayload.payload, queuedPayload.branchTarget)
  }
}

function readBlock(text, labels, stopLabels) {
  const source = String(text || '').replace(/\r/g, '')
  for (const label of labels) {
    const start = source.indexOf(label)
    if (start < 0) continue
    const valueStart = start + label.length
    let valueEnd = source.length
    for (const stopLabel of stopLabels) {
      const stop = source.indexOf(`\n${stopLabel}`, valueStart)
      if (stop >= 0) valueEnd = Math.min(valueEnd, stop)
    }
    return source.slice(valueStart, valueEnd).trim()
  }
  return ''
}

function cleanRestoredInput(value) {
  const text = String(value || '').trim()
  return /^<留空[，,]/.test(text) ? '' : text
}

function parseStoredTurnInput(userInput) {
  const stopLabels = ['行动/背景/希望响应：', '主角台词：', '行动：', '台词：', '空白补全：']
  const action = cleanRestoredInput(readBlock(userInput, ['行动/背景/希望响应：', '行动：'], stopLabels))
  const dialogue = cleanRestoredInput(readBlock(userInput, ['主角台词：', '台词：'], stopLabels))
  const autoCompleteText = readBlock(userInput, ['空白补全：'], stopLabels)
  const autoComplete = autoCompleteText ? autoCompleteText.includes('开启') : true
  if (!action && !dialogue && !autoCompleteText) {
    return { action: String(userInput || '').trim(), dialogue: '', autoComplete: true }
  }
  return { action, dialogue, autoComplete }
}

function clearBranchEdit() {
  branchEditTarget.value = null
}

async function deleteFromEntry(entry) {
  const turnId = entry.id || entry.turn_id || 0
  if (!entry.turn_number) return
  const restored = parseStoredTurnInput(entry.user_input)
  actionInput.value = restored.action
  dialogueInput.value = restored.dialogue
  autoCompleteBlank.value = restored.autoComplete
  branchEditTarget.value = {
    turn_id: turnId,
    game_id: gameStore.currentGameId,
    turn_number: entry.turn_number
  }
  streamStatus.value = `已载入第 ${entry.turn_number} 轮输入，修改后点击“重新分支”。`
  await nextTick()
  actionInputRef.value?.focus()
}

async function regenerateEntry(entry) {
  const turnId = entry.id || entry.turn_id || 0
  if (!entry.turn_number) return
  if (!window.confirm('确定重新生成这一轮吗？系统会先回到这一轮之前，再用同一句玩家行动重新推进。')) return
  await streamTurn(async (onEvent) => {
    await regenerateTurnStream(turnId, onEvent, { game_id: gameStore.currentGameId, turn_number: entry.turn_number })
    await gameStore.loadCurrentGame()
  })
}

onMounted(() => {
  rightRailWidth.value = clampRightRailWidth(rightRailWidth.value)
  loadAll()
})
</script>
