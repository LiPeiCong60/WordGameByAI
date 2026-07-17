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
        <div v-if="!characters.length && !ui.loading" class="resource-empty illustrated-empty compact-empty">
          <span class="empty-icon"><UsersRound :size="27" /></span>
          <h3>故事里还没有角色</h3>
          <p>从右侧创建主角或 NPC，系统会自动为角色匹配头像。</p>
        </div>
      </div>
    </div>
    <div class="panel character-editor-panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑角色' : '新增角色' }}</h1></header>
      <section class="character-avatar-editor">
        <CharacterAvatar :character="form" :avatar-url="form.avatar_url" :size="108" shape="rounded" show-auto-badge />
        <div class="character-avatar-copy">
          <span class="eyebrow">CHARACTER PORTRAIT</span>
          <h2>{{ form.name || '等待命名的角色' }}</h2>
          <p v-if="!form.avatar_url">已根据当前标签智能匹配“{{ matchedAvatar.label }}”</p>
          <p v-else>正在使用你上传的专属头像</p>
          <div class="button-row avatar-actions">
            <label v-if="form.id" class="file-button">
              <Upload :size="16" />上传头像
              <input type="file" accept="image/png,image/jpeg,image/webp" @change="handleAvatar" />
            </label>
            <button v-if="form.id && form.avatar_url" type="button" @click="restoreSmartAvatar"><WandSparkles :size="16" />恢复智能头像</button>
            <button type="button" @click="avatarLibraryOpen = true"><Images :size="16" />查看头像库</button>
          </div>
          <small v-if="!form.id">保存角色后可以上传专属头像；不上传也会自动匹配。</small>
        </div>
      </section>
      <form class="form-grid" @submit.prevent="save">
        <h3 class="form-section wide">基本信息</h3>
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
        <h3 class="form-section wide">当前状态与关系</h3>
        <label class="field"><span>状态</span><select v-model="form.status"><option v-for="option in characterStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
        <label class="field"><span>心情</span><input v-model="form.mood" /></label>
        <label class="field"><span>与主角关系</span><input v-model="form.relationship_to_player" /></label>
        <label class="field"><span>关系值</span><input v-model.number="form.relationship_score" type="number" min="-100" max="100" /></label>
        <label class="field"><span>好感度</span><input v-model.number="form.affection_score" type="number" min="0" max="100" /></label>
        <label class="field"><span>信任度</span><input v-model.number="form.trust_score" type="number" min="0" max="100" /></label>
        <label class="field"><span>张力</span><input v-model.number="form.tension_score" type="number" min="0" max="100" /></label>
        <h3 class="form-section wide">人物设定</h3>
        <label class="field wide"><span>外貌</span><textarea v-model="form.appearance" rows="3" /></label>
        <label class="field wide"><span>性格</span><textarea v-model="form.personality" rows="3" /></label>
        <label class="field wide"><span>说话风格</span><textarea v-model="form.speech_style" rows="3" /></label>
        <label class="field wide"><span>能力</span><textarea v-model="form.abilities" rows="3" /></label>
        <label class="field wide"><span>当前目标</span><textarea v-model="form.current_goal" rows="3" /></label>
        <label class="field wide"><span>隐藏目标</span><textarea v-model="form.hidden_goal" rows="3" /></label>
        <label class="field wide"><span>记忆摘要</span><textarea v-model="form.memory_summary" rows="3" /></label>
        <h3 class="form-section wide">高级设置</h3>
        <label class="check-field"><input v-model="form.agent_enabled" type="checkbox" />启用 NPC 子 Agent</label>
        <JsonEditor v-model="form.extra_attrs" class="wide" />
        <div class="form-action-bar wide">
          <button type="submit" class="primary"><Save :size="17" />保存角色</button>
          <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
          <button v-if="form.id" type="button" class="danger-button" @click="remove(form.id)"><Trash2 :size="17" />删除</button>
        </div>
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

  <div v-if="avatarLibraryOpen" class="modal-backdrop" @click.self="avatarLibraryOpen = false">
    <section class="avatar-library-dialog" role="dialog" aria-modal="true" aria-labelledby="avatar-library-title">
      <header>
        <div><span class="eyebrow">SMART AVATAR LIBRARY</span><h2 id="avatar-library-title">AI 漫剧角色头像库</h2><p>角色没有上传图片时，会按照性别、年龄、身份、外貌和性格自动匹配。</p></div>
        <button type="button" class="icon-button" aria-label="关闭头像库" @click="avatarLibraryOpen = false"><X :size="19" /></button>
      </header>
      <div class="avatar-library-grid">
        <article v-for="profile in avatarProfiles" :key="profile.id" :class="{ active: profile.id === matchedAvatar.id }">
          <img :src="profile.assetPath" :alt="profile.label" loading="lazy" decoding="async" />
          <div><strong>{{ profile.label }}</strong><small>{{ ageLabel(profile.age) }} · {{ profile.gender === 'female' ? '女性' : '男性' }}</small></div>
          <span v-if="profile.id === matchedAvatar.id">当前匹配</span>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Images, RefreshCw, RotateCcw, Save, Trash2, Upload, UsersRound, WandSparkles, X } from 'lucide-vue-next'
import CharacterAvatar from '../components/CharacterAvatar.vue'
import CharacterCard from '../components/CharacterCard.vue'
import JsonEditor from '../components/JsonEditor.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { createCharacter, deleteAvatar, deleteCharacter, listCharacters, uploadAvatar, updateCharacter } from '../api/characters'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { characterStatusLabels, optionsFrom, roleTypeLabels } from '../utils/labels'
import { ensureStarterCharacters } from '../utils/starterCharacters'
import { DEFAULT_AVATAR_PROFILES, matchDefaultAvatar } from '../utils/defaultAvatars'

const gameStore = useGameStore()
const ui = useUiStore()
defineProps({
  embedded: { type: Boolean, default: false }
})
const characters = ref([])
const autoCreated = ref(false)
const avatarLibraryOpen = ref(false)
const avatarProfiles = DEFAULT_AVATAR_PROFILES
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
const matchedAvatar = computed(() => matchDefaultAvatar(form))

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
  if (!window.confirm(`确定删除角色“${form.name || '未命名角色'}”吗？此操作无法撤销。`)) return
  await ui.run(async () => {
    await deleteCharacter(id)
    reset()
    await load()
  })
}

async function restoreSmartAvatar() {
  if (!form.id || !form.avatar_url) return
  await ui.run(async () => {
    await deleteAvatar(form.id)
    form.avatar_url = ''
    await load()
  })
}

function ageLabel(age) {
  return ({ child: '儿童', teen: '少年', young: '青年', middle: '中年', senior: '长者' })[age] || '角色'
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
