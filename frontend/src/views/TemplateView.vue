<template>
  <section class="template-workspace">
    <div class="panel template-list-panel">
      <header class="panel-header">
        <h1>模板</h1>
        <div class="button-row">
          <button type="button" class="icon-button" title="新增模板" @click="reset"><Plus :size="17" /></button>
          <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
        </div>
      </header>
      <div class="stack-list">
        <article v-for="template in templates" :key="template.id" class="list-card" :class="{ active: form.id === template.id }" @click="openTemplate(template)">
          <header>
            <h3>{{ template.name }}</h3>
            <span class="pill">{{ templateVisibilityLabel(template) }}</span>
          </header>
          <p>{{ template.default_rules }}</p>
          <footer>{{ template.world_type }} · {{ template.tone }} · {{ template.genre }}</footer>
          <div class="button-row">
            <button type="button" @click.stop="openTemplate(template)"><Pencil :size="17" />{{ canEditTemplate(template) ? '修改设计' : '复制设计' }}</button>
            <button v-if="canEditTemplate(template)" type="button" @click.stop="remove(template.id)"><Trash2 :size="17" /></button>
          </div>
        </article>
      </div>
    </div>

    <div class="panel template-editor-panel">
      <header class="panel-header">
        <div>
          <span class="step-badge">模板蓝图</span>
          <h1>{{ form.id ? `编辑 ${form.name || '模板'}` : '新增模板' }}</h1>
        </div>
        <button v-if="form.id && canEditTemplate(form)" type="button" @click="remove(form.id)"><Trash2 :size="17" />删除模板</button>
      </header>
      <div class="notice">
        <p>模板是存档的基础定义；用模板创建的新存档会复制这些默认值，已创建的存档不会被模板修改反向覆盖。</p>
      </div>
      <form class="form-grid" @submit.prevent="save">
        <h2 class="form-section wide">模板基础</h2>
        <label class="field"><span>名称</span><input v-model="form.name" required /></label>
        <label class="field"><span>题材</span><input v-model="form.genre" /></label>
        <label class="field"><span>世界类型</span><input v-model="form.world_type" /></label>
        <label class="field"><span>基调</span><input v-model="form.tone" /></label>
        <label v-if="auth.isAdmin" class="check-field wide">
          <input v-model="form.is_public" type="checkbox" />
          公开模板
        </label>
        <label class="field wide"><span>描述</span><textarea v-model="form.description" rows="3" /></label>

        <h2 class="form-section wide">新存档初始设定</h2>
        <label class="field wide"><span>默认文风</span><textarea v-model="form.default_style_guide" rows="5" /></label>
        <label class="field wide"><span>默认规则</span><textarea v-model="form.default_rules" rows="5" /></label>

        <section class="wide starter-character-designer">
          <header class="inline-section-header">
            <h2>开局角色设计</h2>
            <div class="button-row">
              <button type="button" @click="addStarterCharacter('protagonist')"><UserPlus :size="17" />主角</button>
              <button type="button" @click="addStarterCharacter('npc')"><UserPlus :size="17" />NPC</button>
            </div>
          </header>

          <div class="starter-character-grid">
            <article v-for="(character, index) in starterCharacters" :key="character.local_id" class="starter-character-card">
              <header>
                <label class="field"><span>姓名</span><input v-model="character.name" @input="writeCharactersToJson" /></label>
                <label class="field">
                  <span>类型</span>
                  <select v-model="character.role_type" @change="writeCharactersToJson">
                    <option value="protagonist">主角</option>
                    <option value="npc">NPC</option>
                  </select>
                </label>
                <button type="button" class="icon-button" title="移除角色" @click="removeStarterCharacter(index)">
                  <Trash2 :size="17" />
                </button>
              </header>

              <div class="starter-character-fields">
                <label class="field"><span>性别</span><input v-model="character.gender" @input="writeCharactersToJson" /></label>
                <label class="field"><span>年龄</span><input v-model="character.age" @input="writeCharactersToJson" /></label>
                <label class="field"><span>身份</span><input v-model="character.race_or_identity" @input="writeCharactersToJson" /></label>
                <label class="field"><span>头像URL</span><input v-model="character.avatar_url" @input="writeCharactersToJson" /></label>
                <label class="field"><span>位置</span><input v-model="character.current_location" @input="writeCharactersToJson" /></label>
                <label class="field"><span>状态</span><input v-model="character.status" @input="writeCharactersToJson" /></label>
                <label class="field"><span>心情</span><input v-model="character.mood" @input="writeCharactersToJson" /></label>
                <label class="field"><span>与玩家关系</span><input v-model="character.relationship_to_player" @input="writeCharactersToJson" /></label>
                <label class="field"><span>关系</span><input v-model.number="character.relationship_score" type="number" @input="writeCharactersToJson" /></label>
                <label class="field"><span>好感</span><input v-model.number="character.affection_score" type="number" @input="writeCharactersToJson" /></label>
                <label class="field"><span>信任</span><input v-model.number="character.trust_score" type="number" @input="writeCharactersToJson" /></label>
                <label class="field"><span>张力</span><input v-model.number="character.tension_score" type="number" @input="writeCharactersToJson" /></label>
                <label class="check-field"><input v-model="character.agent_enabled" type="checkbox" @change="writeCharactersToJson" />启用 NPC 子 Agent</label>
                <label class="field wide"><span>外貌</span><textarea v-model="character.appearance" rows="3" @input="writeCharactersToJson" /></label>
                <label class="field wide"><span>性格</span><textarea v-model="character.personality" rows="3" @input="writeCharactersToJson" /></label>
                <label class="field wide"><span>说话风格</span><textarea v-model="character.speech_style" rows="3" @input="writeCharactersToJson" /></label>
                <label class="field wide"><span>能力</span><textarea v-model="character.abilities" rows="3" @input="writeCharactersToJson" /></label>
                <label class="field wide"><span>当前目标</span><textarea v-model="character.current_goal" rows="3" @input="writeCharactersToJson" /></label>
                <label class="field wide"><span>隐藏目标</span><textarea v-model="character.hidden_goal" rows="3" @input="writeCharactersToJson" /></label>
                <label class="field wide"><span>长期记忆</span><textarea v-model="character.memory_summary" rows="3" @input="writeCharactersToJson" /></label>
                <label class="field wide"><span>扩展属性 JSON</span><textarea v-model="character.extra_attrs" rows="3" @input="writeCharactersToJson" /></label>
              </div>
            </article>
          </div>
        </section>

        <JsonEditor v-model="form.default_character_fields" class="wide" label="默认角色字段 JSON" />
        <button type="submit" class="primary"><Save :size="17" />保存模板</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
      </form>
    </div>

    <aside class="template-agent-panel">
      <SectionAgentPanel
        global
        scope="模板"
        title="当前模板控制智能体"
        description="针对中间正在编辑的模板蓝图生成修改方案。确认后写入模板库，不会反向覆盖已创建存档。"
        placeholder="例如：根据当前模板补全开局角色、优化默认规则，或把它改成古风权谋恋爱。"
        :context="templateAgentContext"
        :quick-prompts="templateAgentPrompts"
        @applied="handleAgentApplied"
      />
    </aside>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { Pencil, Plus, RefreshCw, RotateCcw, Save, Trash2, UserPlus } from 'lucide-vue-next'
import JsonEditor from '../components/JsonEditor.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { createTemplate, deleteTemplate, listTemplates, updateTemplate } from '../api/templates'
import { useAuthStore } from '../stores/authStore'
import { useUiStore } from '../stores/uiStore'

const ui = useUiStore()
const auth = useAuthStore()
const templates = ref([])
const starterCharacters = ref([])
let characterLocalId = 1
let writingCharacterJson = false

const templateAgentPrompts = [
  '根据当前模板补全一套更完整的开局角色设计。',
  '优化当前模板的默认文风和默认规则，让新存档更稳定。',
  '检查当前模板还有哪些初始设定缺失，并给出可执行修改方案。'
]

const starterJson = () => JSON.stringify({
  characters: [
    serializeStarterCharacter(blankStarterCharacter('protagonist', '主角')),
    serializeStarterCharacter(blankStarterCharacter('npc', '重要角色'))
  ]
}, null, 2)

const blank = () => ({
  id: null,
  owner_user_id: null,
  is_public: false,
  name: '',
  genre: '',
  world_type: '',
  tone: '',
  description: '',
  default_style_guide: '',
  default_rules: '',
  default_character_fields: starterJson()
})
const form = reactive(blank())

const templateAgentContext = computed(() => {
  const characters = starterCharacters.value.map((character) => ({
    name: character.name,
    role_type: character.role_type,
    avatar_url: character.avatar_url,
    gender: character.gender,
    age: character.age,
    race_or_identity: character.race_or_identity,
    appearance: character.appearance,
    personality: character.personality,
    speech_style: character.speech_style,
    abilities: character.abilities,
    current_location: character.current_location,
    status: character.status,
    mood: character.mood,
    relationship_to_player: character.relationship_to_player,
    relationship_score: character.relationship_score,
    affection_score: character.affection_score,
    trust_score: character.trust_score,
    tension_score: character.tension_score,
    current_goal: character.current_goal,
    hidden_goal: character.hidden_goal,
    memory_summary: character.memory_summary,
    extra_attrs: character.extra_attrs,
    agent_enabled: character.agent_enabled
  }))
  return JSON.stringify({
    current_template_id: form.id,
    name: form.name,
    genre: form.genre,
    world_type: form.world_type,
    tone: form.tone,
    description: form.description,
    default_style_guide: form.default_style_guide,
    default_rules: form.default_rules,
    starter_characters: characters
  }, null, 2)
})

function reset() {
  Object.assign(form, blank())
  syncCharactersFromJson()
}

function edit(template) {
  Object.assign(form, {
    ...template,
    is_public: template.owner_user_id === null || template.owner_user_id === undefined
  })
  syncCharactersFromJson()
}

function canEditTemplate(template) {
  return Boolean(auth.isAdmin || template.owner_user_id === auth.user?.id)
}

function templateVisibilityLabel(template) {
  if (template.owner_user_id === null || template.owner_user_id === undefined) return '公共模板'
  if (template.owner_user_id === auth.user?.id) return '我的模板'
  return '用户模板'
}

function copyTemplate(template) {
  Object.assign(form, {
    ...template,
    id: null,
    owner_user_id: auth.user?.id ?? null,
    is_public: false,
    name: `${template.name || '模板'} 副本`
  })
  syncCharactersFromJson()
}

function openTemplate(template) {
  if (canEditTemplate(template)) edit(template)
  else copyTemplate(template)
}

function blankStarterCharacter(roleType = 'npc', name = '') {
  return {
    local_id: characterLocalId++,
    name: name || (roleType === 'protagonist' ? '主角' : '重要角色'),
    role_type: roleType,
    gender: '',
    age: '',
    race_or_identity: '',
    appearance: '',
    personality: '',
    speech_style: '',
    abilities: '',
    current_location: '',
    status: 'normal',
    mood: '平静',
    relationship_to_player: roleType === 'protagonist' ? '自己' : '待定',
    relationship_score: 0,
    affection_score: 0,
    trust_score: 0,
    tension_score: 0,
    current_goal: '',
    hidden_goal: '',
    memory_summary: '故事刚开始，角色还没有长期记忆。',
    agent_enabled: roleType !== 'protagonist',
    extra_attrs: '{}'
  }
}

function parseStarterCharacters(value) {
  try {
    const parsed = JSON.parse(value || '{}')
    if (Array.isArray(parsed)) return parsed
    if (Array.isArray(parsed.characters)) return parsed.characters
    if (Array.isArray(parsed.starter_characters)) return parsed.starter_characters
    const result = []
    if (parsed.protagonist && typeof parsed.protagonist === 'object') result.push({ ...parsed.protagonist, role_type: 'protagonist' })
    if (Array.isArray(parsed.npcs)) result.push(...parsed.npcs)
    return result
  } catch {
    return null
  }
}

function normalizeStarterCharacter(data, fallbackRole = 'npc') {
  const roleType = data.role_type || fallbackRole
  return {
    ...blankStarterCharacter(roleType, data.name),
    ...data,
    local_id: characterLocalId++,
    role_type: roleType,
    relationship_score: Number(data.relationship_score ?? 0),
    affection_score: Number(data.affection_score ?? 0),
    trust_score: Number(data.trust_score ?? 0),
    tension_score: Number(data.tension_score ?? 0),
    agent_enabled: data.agent_enabled ?? roleType !== 'protagonist'
  }
}

function syncCharactersFromJson() {
  const parsed = parseStarterCharacters(form.default_character_fields)
  if (!parsed) return
  starterCharacters.value = parsed.map((item) => normalizeStarterCharacter(item))
}

function serializeStarterCharacter(character) {
  const { local_id, ...data } = character
  return data
}

function writeCharactersToJson() {
  writingCharacterJson = true
  form.default_character_fields = JSON.stringify({
    characters: starterCharacters.value.map(serializeStarterCharacter)
  }, null, 2)
  nextTick(() => {
    writingCharacterJson = false
  })
}

function addStarterCharacter(roleType) {
  starterCharacters.value.push(blankStarterCharacter(roleType))
  writeCharactersToJson()
}

function removeStarterCharacter(index) {
  starterCharacters.value.splice(index, 1)
  writeCharactersToJson()
}

async function load() {
  await ui.run(async () => {
    templates.value = await listTemplates()
  })
}

async function save() {
  writeCharactersToJson()
  const data = { ...form }
  delete data.id
  await ui.run(async () => {
    const saved = form.id ? await updateTemplate(form.id, data) : await createTemplate(data)
    await load()
    edit(saved)
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteTemplate(id)
    if (form.id === id) reset()
    await load()
  })
}

async function handleAgentApplied() {
  const currentId = form.id
  await load()
  if (!currentId) return
  const updated = templates.value.find((template) => template.id === currentId)
  if (updated) edit(updated)
}

onMounted(load)

watch(
  () => form.default_character_fields,
  () => {
    if (!writingCharacterJson) syncCharactersFromJson()
  }
)

syncCharactersFromJson()
</script>
