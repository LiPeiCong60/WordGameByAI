<template>
  <section class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>存档</h1>
        <button type="button" class="icon-button" title="刷新" @click="load">
          <RefreshCw :size="17" />
        </button>
      </header>
      <div class="game-list">
        <article v-for="game in games" :key="game.id" class="game-row" :class="{ active: game.id === gameStore.currentGameId }">
          <div>
            <h2>{{ game.title }}</h2>
            <p>{{ game.genre || '未设置题材' }} · {{ game.world_type || '未设置世界类型' }}</p>
          </div>
          <div class="button-row">
            <button type="button" class="primary" @click="enterGame(game)">
              <Play :size="17" />
              进入游戏
            </button>
            <button type="button" title="导出" @click="downloadExport(game.id)">
              <Download :size="17" />
            </button>
            <button type="button" title="删除" @click="remove(game.id)">
              <Trash2 :size="17" />
            </button>
          </div>
        </article>
      </div>
    </div>

    <div class="panel">
      <header class="panel-header">
        <h1>创建存档</h1>
      </header>
      <form class="form-grid" @submit.prevent="submit">
        <label class="field">
          <span>模板</span>
          <select v-model.number="selectedTemplateId" @change="applyTemplate">
            <option :value="0">不使用模板</option>
            <option v-for="template in templates" :key="template.id" :value="template.id">{{ template.name }}</option>
          </select>
        </label>
        <label class="field"><span>标题</span><input v-model="form.title" required /></label>
        <label class="field"><span>题材</span><input v-model="form.genre" /></label>
        <label class="field"><span>世界类型</span><input v-model="form.world_type" /></label>
        <label class="field"><span>基调</span><input v-model="form.tone" /></label>
        <label class="field"><span>叙事视角</span><input v-model="form.narrative_perspective" /></label>
        <label class="field wide"><span>文风规则</span><textarea v-model="form.style_guide" rows="4" /></label>
        <label class="field wide"><span>世界规则摘要</span><textarea v-model="form.rules_summary" rows="4" /></label>
        <button type="submit" class="primary">
          <Plus :size="17" />
          创建存档
        </button>
        <label class="file-button">
          <Upload :size="17" />
          导入存档 JSON
          <input type="file" accept="application/json" @change="handleImport" />
        </label>
      </form>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Download, Play, Plus, RefreshCw, Trash2, Upload } from 'lucide-vue-next'
import { createGame, deleteGame, exportGame, importGame, listGames } from '../api/games'
import { listTemplates } from '../api/templates'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'

const router = useRouter()
const gameStore = useGameStore()
const ui = useUiStore()
const games = ref([])
const templates = ref([])
const selectedTemplateId = ref(0)
const form = reactive({
  title: '',
  genre: '',
  world_type: '',
  tone: '',
  narrative_perspective: '第二人称',
  style_guide: '',
  rules_summary: '',
  current_state: ''
})

async function load() {
  await ui.run(async () => {
    games.value = await listGames()
    templates.value = await listTemplates()
  })
}

function applyTemplate() {
  const template = templates.value.find((item) => item.id === selectedTemplateId.value)
  if (!template) return
  form.genre = template.genre
  form.world_type = template.world_type
  form.tone = template.tone
  form.style_guide = template.default_style_guide
  form.rules_summary = template.default_rules
  if (!form.title) form.title = `${template.name}存档`
}

async function submit() {
  await ui.run(async () => {
    const game = await createGame({ ...form, template_id: selectedTemplateId.value || null })
    await gameStore.loadCurrentGame(game.id)
    await load()
    router.push('/play')
  })
}

async function enterGame(game) {
  await ui.run(async () => {
    await gameStore.loadCurrentGame(game.id)
    router.push('/play')
  })
}

async function remove(id) {
  if (!window.confirm('确定彻底删除这个存档吗？角色、世界、设定、剧情记录和管理对话都会一起删除。')) return
  await ui.run(async () => {
    await deleteGame(id)
    if (gameStore.currentGameId === id) gameStore.clear()
    await load()
  })
}

async function downloadExport(id) {
  const data = await exportGame(id)
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `narrative-agent-save-${id}.json`
  link.click()
  URL.revokeObjectURL(url)
}

function handleImport(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async () => {
    await ui.run(async () => {
      const payload = JSON.parse(reader.result)
      const result = await importGame(payload)
      await gameStore.loadCurrentGame(result.game.id)
      await load()
    })
  }
  reader.readAsText(file)
}

onMounted(load)
</script>
