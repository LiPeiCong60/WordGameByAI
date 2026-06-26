<template>
  <section class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>模板</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <div class="stack-list">
        <article v-for="template in templates" :key="template.id" class="list-card">
          <header>
            <h3>{{ template.name }}</h3>
            <span class="pill">{{ template.genre }}</span>
          </header>
          <p>{{ template.default_rules }}</p>
          <footer>{{ template.world_type }} · {{ template.tone }}</footer>
          <div class="button-row">
            <button type="button" @click="edit(template)"><Pencil :size="17" /></button>
            <button type="button" @click="remove(template.id)"><Trash2 :size="17" /></button>
          </div>
        </article>
      </div>
    </div>
    <div class="panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑模板' : '新增模板' }}</h1></header>
      <form class="form-grid" @submit.prevent="save">
        <label class="field"><span>名称</span><input v-model="form.name" required /></label>
        <label class="field"><span>题材</span><input v-model="form.genre" /></label>
        <label class="field"><span>世界类型</span><input v-model="form.world_type" /></label>
        <label class="field"><span>基调</span><input v-model="form.tone" /></label>
        <label class="field wide"><span>描述</span><textarea v-model="form.description" rows="3" /></label>
        <label class="field wide"><span>默认文风</span><textarea v-model="form.default_style_guide" rows="5" /></label>
        <label class="field wide"><span>默认规则</span><textarea v-model="form.default_rules" rows="5" /></label>
        <JsonEditor v-model="form.default_character_fields" class="wide" label="默认角色字段 JSON" />
        <button type="submit" class="primary"><Save :size="17" />保存</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
      </form>
    </div>
    <SectionAgentPanel
      global
      scope="模板"
      title="模板智能体"
      description="讨论并生成题材模板、默认规则、默认文风和默认角色字段，确认后写入全局模板库。"
      placeholder="例如：帮我做一个古风权谋恋爱模板，要带默认角色字段。"
      @applied="load"
    />
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Pencil, RefreshCw, RotateCcw, Save, Trash2 } from 'lucide-vue-next'
import JsonEditor from '../components/JsonEditor.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { createTemplate, deleteTemplate, listTemplates, updateTemplate } from '../api/templates'
import { useUiStore } from '../stores/uiStore'

const ui = useUiStore()
const templates = ref([])
const blank = () => ({ id: null, name: '', genre: '', world_type: '', tone: '', description: '', default_style_guide: '', default_rules: '', default_character_fields: '{}' })
const form = reactive(blank())

function reset() {
  Object.assign(form, blank())
}

function edit(template) {
  Object.assign(form, template)
}

async function load() {
  await ui.run(async () => {
    templates.value = await listTemplates()
  })
}

async function save() {
  const data = { ...form }
  delete data.id
  await ui.run(async () => {
    if (form.id) await updateTemplate(form.id, data)
    else await createTemplate(data)
    reset()
    await load()
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteTemplate(id)
    await load()
  })
}

onMounted(load)
</script>
