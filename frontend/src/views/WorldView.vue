<template>
  <SaveContextBar v-if="!embedded" @changed="load" />
  <NoGamePrompt v-if="!gameStore.currentGameId" />
  <section v-else class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>世界 / 副本</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <div class="stack-list">
        <article v-for="world in worlds" :key="world.id" class="list-card" :class="{ active: world.id === gameStore.currentGame?.current_story_world_id }">
          <header>
            <h3>{{ world.name }}</h3>
            <span class="pill">{{ world.world_type }}</span>
          </header>
          <p>{{ world.summary || world.current_status }}</p>
          <footer>任务：{{ world.mission_objective || '-' }} · 偏移度 {{ world.plot_deviation }}</footer>
          <div class="button-row">
            <button type="button" @click="edit(world)"><Pencil :size="17" /></button>
            <button type="button" @click="makeCurrent(world.id)"><Flag :size="17" /></button>
            <button type="button" @click="remove(world.id)"><Trash2 :size="17" /></button>
          </div>
        </article>
      </div>
    </div>
    <div class="panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑世界' : '新增世界' }}</h1></header>
      <form class="form-grid" @submit.prevent="save">
        <label class="field"><span>名称</span><input v-model="form.name" required /></label>
        <label class="field"><span>世界类型</span><input v-model="form.world_type" /></label>
        <label class="field wide"><span>摘要</span><textarea v-model="form.summary" rows="3" /></label>
        <label class="field wide"><span>当前状态</span><textarea v-model="form.current_status" rows="3" /></label>
        <label class="field wide"><span>任务目标</span><textarea v-model="form.mission_objective" rows="3" /></label>
        <label class="field"><span>完成条件</span><input v-model="form.completion_condition" /></label>
        <label class="field"><span>失败条件</span><input v-model="form.failure_condition" /></label>
        <label class="field"><span>剧情偏移度</span><input v-model.number="form.plot_deviation" type="number" /></label>
        <button type="submit" class="primary"><Save :size="17" />保存</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
      </form>
    </div>
    <SectionAgentPanel
      v-if="!embedded"
      scope="世界"
      title="世界智能体"
      description="讨论世界、副本、任务目标、完成条件和当前状态，确认后写入世界数据。"
      placeholder="例如：帮我把当前现代都市扩展成三章结构，并补任务目标和失败条件。"
      @applied="load"
    />
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Flag, Pencil, RefreshCw, RotateCcw, Save, Trash2 } from 'lucide-vue-next'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { createStoryWorld, deleteStoryWorld, getStoryWorlds, setCurrentStoryWorld, updateStoryWorld } from '../api/worlds'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'

const gameStore = useGameStore()
const ui = useUiStore()
defineProps({
  embedded: { type: Boolean, default: false }
})
const worlds = ref([])
const blank = () => ({ id: null, name: '', world_type: '', summary: '', current_status: '', mission_objective: '', completion_condition: '', failure_condition: '', plot_deviation: 0 })
const form = reactive(blank())

function reset() {
  Object.assign(form, blank())
}

function edit(world) {
  Object.assign(form, world)
}

async function load() {
  await ui.run(async () => {
    if (!gameStore.currentGameId) return
    await gameStore.loadCurrentGame()
    worlds.value = await getStoryWorlds(gameStore.currentGameId)
  })
}

async function save() {
  if (!gameStore.currentGameId) return
  const data = { ...form }
  delete data.id
  await ui.run(async () => {
    if (form.id) await updateStoryWorld(form.id, data)
    else await createStoryWorld(gameStore.currentGameId, data)
    reset()
    await load()
  })
}

async function makeCurrent(id) {
  await ui.run(async () => {
    await setCurrentStoryWorld(gameStore.currentGameId, id)
    await load()
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteStoryWorld(id)
    await load()
  })
}

onMounted(load)
</script>
