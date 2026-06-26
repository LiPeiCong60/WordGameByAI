<template>
  <SaveContextBar v-if="!embedded" @changed="load" />
  <NoGamePrompt v-if="!gameStore.currentGameId" />
  <section v-else class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>世界事件</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <EventList :events="events">
        <template #actions="{ event }">
          <button type="button" @click="edit(event)"><Pencil :size="17" /></button>
          <button type="button" @click="remove(event.id)"><Trash2 :size="17" /></button>
        </template>
      </EventList>
    </div>
    <div class="panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑事件' : '新增事件' }}</h1></header>
      <form class="form-grid" @submit.prevent="save">
        <label class="field"><span>标题</span><input v-model="form.title" required /></label>
        <label class="field"><span>类型</span><input v-model="form.event_type" /></label>
        <label class="field"><span>章节</span><input v-model="form.arc_name" /></label>
        <label class="field"><span>相关世界</span><input v-model="form.related_world" /></label>
        <label class="field"><span>地点</span><input v-model="form.location" /></label>
        <label class="field"><span>状态</span><select v-model="form.status"><option v-for="option in eventStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
        <label class="field"><span>重要度</span><input v-model.number="form.importance" type="number" /></label>
        <label class="field wide"><span>摘要</span><textarea v-model="form.summary" rows="4" /></label>
        <label class="field wide"><span>参与者</span><textarea v-model="form.participants" rows="2" /></label>
        <label class="field wide"><span>后果</span><textarea v-model="form.consequence" rows="3" /></label>
        <JsonEditor v-model="form.extra_attrs" class="wide" />
        <button type="submit" class="primary"><Save :size="17" />保存</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
        <button v-if="form.id" type="button" @click="remove(form.id)"><Trash2 :size="17" />删除</button>
      </form>
    </div>
    <SectionAgentPanel
      v-if="!embedded"
      scope="事件"
      title="事件智能体"
      description="讨论剧情事件、章节节点、参与者、后果和重要度，确认后写入事件数据。"
      placeholder="例如：帮我整理一条主角和重要 NPC 第一次产生误会的重要事件。"
      @applied="load"
    />
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Pencil, RefreshCw, RotateCcw, Save, Trash2 } from 'lucide-vue-next'
import EventList from '../components/EventList.vue'
import JsonEditor from '../components/JsonEditor.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { createEvent, deleteEvent, listEvents, updateEvent } from '../api/events'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { eventStatusLabels, optionsFrom } from '../utils/labels'

const gameStore = useGameStore()
const ui = useUiStore()
defineProps({
  embedded: { type: Boolean, default: false }
})
const events = ref([])
const eventStatusOptions = optionsFrom(eventStatusLabels)
const blank = () => ({ id: null, title: '', event_type: '背景事件', arc_name: '', related_world: '', summary: '', location: '', participants: '', consequence: '', status: 'active', importance: 5, extra_attrs: '{}' })
const form = reactive(blank())

function reset() {
  Object.assign(form, blank())
}

function edit(event) {
  Object.assign(form, event)
}

async function load() {
  await ui.run(async () => {
    if (!gameStore.currentGameId) return
    events.value = await listEvents(gameStore.currentGameId)
  })
}

async function save() {
  const data = { ...form }
  delete data.id
  await ui.run(async () => {
    if (form.id) await updateEvent(form.id, data)
    else await createEvent(gameStore.currentGameId, data)
    reset()
    await load()
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteEvent(id)
    reset()
    await load()
  })
}

onMounted(load)
</script>
