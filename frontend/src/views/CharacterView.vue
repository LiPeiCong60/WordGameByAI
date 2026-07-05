<template>
  <SaveContextBar v-if="!embedded" @changed="load" />
  <NoGamePrompt v-if="!gameStore.currentGameId" />
  <section v-else class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>角色</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <div v-if="autoCreated" class="notice">
        <p>已为当前存档自动创建开场主角和重要 NPC，你可以直接点击角色卡继续修改。</p>
      </div>
      <div class="npc-grid">
        <CharacterCard v-for="character in characters" :key="character.id" :character="character" @click="edit(character)" />
      </div>
    </div>
    <div class="panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑角色' : '新增角色' }}</h1></header>
      <form class="form-grid" @submit.prevent="save">
        <label class="field"><span>姓名</span><input v-model="form.name" required /></label>
        <label class="field">
          <span>角色类型</span>
          <select v-model="form.role_type">
            <option v-for="option in roleTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="field"><span>性别</span><input v-model="form.gender" /></label>
        <label class="field"><span>年龄</span><input v-model="form.age" /></label>
        <label class="field"><span>身份 / 种族</span><input v-model="form.race_or_identity" /></label>
        <label class="field"><span>当前位置</span><input v-model="form.current_location" /></label>
        <label class="field"><span>状态</span><select v-model="form.status"><option v-for="option in characterStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
        <label class="field"><span>心情</span><input v-model="form.mood" /></label>
        <label class="field"><span>与主角关系</span><input v-model="form.relationship_to_player" /></label>
        <label class="field"><span>关系值</span><input v-model.number="form.relationship_score" type="number" min="-100" max="100" /></label>
        <label class="field"><span>好感度</span><input v-model.number="form.affection_score" type="number" min="0" max="100" /></label>
        <label class="field"><span>信任度</span><input v-model.number="form.trust_score" type="number" min="0" max="100" /></label>
        <label class="field"><span>张力</span><input v-model.number="form.tension_score" type="number" min="0" max="100" /></label>
        <label class="field wide"><span>外貌</span><textarea v-model="form.appearance" rows="3" /></label>
        <label class="field wide"><span>性格</span><textarea v-model="form.personality" rows="3" /></label>
        <label class="field wide"><span>说话风格</span><textarea v-model="form.speech_style" rows="3" /></label>
        <label class="field wide"><span>能力</span><textarea v-model="form.abilities" rows="3" /></label>
        <label class="field wide"><span>当前目标</span><textarea v-model="form.current_goal" rows="3" /></label>
        <label class="field wide"><span>隐藏目标</span><textarea v-model="form.hidden_goal" rows="3" /></label>
        <label class="field wide"><span>记忆摘要</span><textarea v-model="form.memory_summary" rows="3" /></label>
        <label class="check-field"><input v-model="form.agent_enabled" type="checkbox" />启用 NPC 子 Agent</label>
        <JsonEditor v-model="form.extra_attrs" class="wide" />
        <label v-if="form.id" class="file-button">
          <Upload :size="17" />
          上传头像
          <input type="file" accept="image/*" @change="handleAvatar" />
        </label>
        <button type="submit" class="primary"><Save :size="17" />保存</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
        <button v-if="form.id" type="button" @click="remove(form.id)"><Trash2 :size="17" />删除</button>
      </form>
    </div>
    <SectionAgentPanel
      v-if="!embedded"
      scope="角色"
      title="角色智能体"
      description="讨论角色设定、关系、能力、子智能体开关，确认后可新增、修改或删除角色。"
      placeholder="例如：帮我设计一个会反复出现的侦探 NPC，性格冷静但不信任主角。"
      @applied="load"
    />
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { RefreshCw, RotateCcw, Save, Trash2, Upload } from 'lucide-vue-next'
import CharacterCard from '../components/CharacterCard.vue'
import JsonEditor from '../components/JsonEditor.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { createCharacter, deleteCharacter, listCharacters, uploadAvatar, updateCharacter } from '../api/characters'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { characterStatusLabels, optionsFrom, roleTypeLabels } from '../utils/labels'
import { ensureStarterCharacters } from '../utils/starterCharacters'

const gameStore = useGameStore()
const ui = useUiStore()
defineProps({
  embedded: { type: Boolean, default: false }
})
const characters = ref([])
const autoCreated = ref(false)
const roleTypeOptions = optionsFrom(roleTypeLabels)
const characterStatusOptions = optionsFrom(characterStatusLabels)
const blank = () => ({
  id: null,
  name: '',
  role_type: 'npc',
  avatar_url: '',
  gender: '',
  age: '',
  race_or_identity: '',
  appearance: '',
  personality: '',
  speech_style: '',
  abilities: '',
  current_location: '',
  status: 'normal',
  mood: '',
  relationship_to_player: '',
  relationship_score: 0,
  affection_score: 0,
  trust_score: 0,
  tension_score: 0,
  current_goal: '',
  hidden_goal: '',
  memory_summary: '',
  agent_enabled: true,
  extra_attrs: '{}'
})
const form = reactive(blank())

function reset() {
  Object.assign(form, blank())
}

function edit(character) {
  Object.assign(form, character)
}

async function load() {
  await ui.run(async () => {
    if (!gameStore.currentGameId) return
    await gameStore.loadCurrentGame()
    const starterResult = await ensureStarterCharacters(gameStore.currentGameId, gameStore.currentGame)
    autoCreated.value = starterResult.created
    characters.value = starterResult.created ? await listCharacters(gameStore.currentGameId) : starterResult.characters
  })
}

async function save() {
  const data = { ...form }
  delete data.id
  await ui.run(async () => {
    if (form.id) await updateCharacter(form.id, data)
    else await createCharacter(gameStore.currentGameId, data)
    reset()
    await load()
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteCharacter(id)
    reset()
    await load()
  })
}

async function handleAvatar(event) {
  const file = event.target.files?.[0]
  if (!file || !form.id) return
  await ui.run(async () => {
    const result = await uploadAvatar(form.id, file)
    form.avatar_url = result.avatar_url
    await load()
  })
}

onMounted(load)
</script>
