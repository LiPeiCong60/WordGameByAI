<template>
  <SaveContextBar v-if="!embedded" @changed="load" />
  <NoGamePrompt v-if="!gameStore.currentGameId" />
  <section v-else class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>世界观</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <LoreList :lore-items="loreItems">
        <template #actions="{ lore }">
          <button type="button" @click="edit(lore)"><Pencil :size="17" /></button>
          <button type="button" @click="remove(lore.id)"><Trash2 :size="17" /></button>
        </template>
      </LoreList>
    </div>
    <div class="panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑世界观' : '新增世界观' }}</h1></header>
      <form class="form-grid" @submit.prevent="save">
        <label class="field"><span>标题</span><input v-model="form.title" required /></label>
        <label class="field"><span>分类</span><input v-model="form.category" /></label>
        <label class="field"><span>权威等级</span><select v-model="form.canon_level"><option v-for="option in canonLevelOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
        <label class="field"><span>重要度</span><input v-model.number="form.importance" type="number" min="1" max="10" /></label>
        <label class="field wide"><span>内容</span><textarea v-model="form.content" rows="6" /></label>
        <button type="submit" class="primary"><Save :size="17" />保存</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
      </form>
      <div class="sub-panel">
        <label class="field wide"><span>LoreAgent 整理</span><textarea v-model="rawLore" rows="5" /></label>
        <button type="button" @click="organize"><Sparkles :size="17" />整理</button>
        <pre v-if="organized">{{ JSON.stringify(organized, null, 2) }}</pre>
        <button v-if="organized" type="button" class="primary" @click="useOrganized"><Check :size="17" />填入表单</button>
      </div>
    </div>
    <SectionAgentPanel
      v-if="!embedded"
      scope="设定"
      title="设定智能体"
      description="和智能体讨论世界观、规则、势力、历史、禁忌，确认后写入设定条目。"
      placeholder="例如：和我一起完善这个都市恋爱世界的家庭背景、公司规则和关键秘密。"
      @applied="load"
    />
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Check, Pencil, RefreshCw, RotateCcw, Save, Sparkles, Trash2 } from 'lucide-vue-next'
import LoreList from '../components/LoreList.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { createLore, deleteLore, listLore, organizeLore, updateLore } from '../api/lore'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { canonLevelLabels, optionsFrom } from '../utils/labels'

const gameStore = useGameStore()
const ui = useUiStore()
defineProps({
  embedded: { type: Boolean, default: false }
})
const loreItems = ref([])
const rawLore = ref('')
const organized = ref(null)
const canonLevelOptions = optionsFrom(canonLevelLabels)
const blank = () => ({ id: null, title: '', category: '其他', content: '', canon_level: 'soft_canon', importance: 5 })
const form = reactive(blank())

function reset() {
  Object.assign(form, blank())
}

function edit(lore) {
  Object.assign(form, lore)
}

async function load() {
  await ui.run(async () => {
    if (!gameStore.currentGameId) return
    loreItems.value = await listLore(gameStore.currentGameId)
  })
}

async function save() {
  const data = { ...form }
  delete data.id
  await ui.run(async () => {
    if (form.id) await updateLore(form.id, data)
    else await createLore(gameStore.currentGameId, data)
    reset()
    await load()
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteLore(id)
    if (form.id === id) reset()
    await load()
  })
}

async function organize() {
  if (!rawLore.value.trim()) return
  organized.value = await organizeLore(gameStore.currentGameId, rawLore.value)
}

function useOrganized() {
  Object.assign(form, organized.value)
  delete form.error
}

onMounted(load)
</script>
