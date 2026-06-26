<template>
  <SaveContextBar v-if="!embedded" @changed="load" />
  <NoGamePrompt v-if="!gameStore.currentGameId" />
  <section v-else class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>物品</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <div class="filters">
        <input v-model="filters.q" placeholder="搜索" />
        <input v-model="filters.type" placeholder="类型" />
        <label><input v-model="filters.keyOnly" type="checkbox" />关键</label>
        <label><input v-model="filters.consumableOnly" type="checkbox" />消耗</label>
        <label><input v-model="filters.equippableOnly" type="checkbox" />装备</label>
      </div>
      <ItemList :items="filteredItems">
        <template #actions="{ item }">
          <button type="button" @click="edit(item)"><Pencil :size="17" /></button>
        </template>
      </ItemList>
    </div>
    <div class="panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑物品' : '新增物品' }}</h1></header>
      <form class="form-grid" @submit.prevent="save">
        <label class="field"><span>名称</span><input v-model="form.name" required /></label>
        <label class="field"><span>类型</span><input v-model="form.item_type" /></label>
        <label class="field">
          <span>状态</span>
          <select v-model="form.status">
            <option v-for="option in itemStateOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="field">
          <span>稀有度</span>
          <select v-model="form.rarity">
            <option v-for="option in rarityOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="field"><span>堆叠上限</span><input v-model.number="form.quantity_limit" type="number" /></label>
        <label class="field"><span>位置</span><input v-model="form.current_location" /></label>
        <label class="field"><span>重要度</span><input v-model.number="form.importance" type="number" /></label>
        <label class="field wide"><span>描述</span><textarea v-model="form.description" rows="3" /></label>
        <label class="field wide"><span>使用条件</span><textarea v-model="form.usable_condition" rows="2" /></label>
        <label class="field wide"><span>效果说明</span><textarea v-model="form.effect_description" rows="2" /></label>
        <label class="check-field"><input v-model="form.is_stackable" type="checkbox" />可堆叠</label>
        <label class="check-field"><input v-model="form.is_equippable" type="checkbox" />可装备</label>
        <label class="check-field"><input v-model="form.is_consumable" type="checkbox" />可消耗</label>
        <label class="check-field"><input v-model="form.is_key_item" type="checkbox" />关键物品</label>
        <label class="check-field"><input v-model="form.is_tradeable" type="checkbox" />可交易</label>
        <label class="check-field"><input v-model="form.is_unique" type="checkbox" />唯一</label>
        <JsonEditor v-model="form.extra_attrs" class="wide" />
        <button type="submit" class="primary"><Save :size="17" />保存</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
        <button v-if="form.id" type="button" @click="remove(form.id)"><Trash2 :size="17" />删除</button>
      </form>
      <div class="sub-panel">
        <h2>分配物品</h2>
        <form class="form-grid" @submit.prevent="assign">
          <label class="field"><span>物品</span><select v-model.number="assignment.item_id"><option v-for="item in items" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
          <label class="field"><span>拥有者类型</span><select v-model="assignment.owner_type"><option v-for="option in ownerTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
          <label class="field"><span>角色</span><select v-model.number="assignment.owner_id" @change="syncOwnerName"><option :value="null">非角色</option><option v-for="character in characters" :key="character.id" :value="character.id">{{ character.name }}</option></select></label>
          <label class="field"><span>拥有者名称</span><input v-model="assignment.owner_name" /></label>
          <label class="field"><span>数量</span><input v-model.number="assignment.quantity" type="number" min="1" /></label>
          <button type="submit" class="primary"><Plus :size="17" />分配</button>
        </form>
      </div>
    </div>
    <SectionAgentPanel
      v-if="!embedded"
      scope="物品"
      title="物品智能体"
      description="讨论道具、装备、消耗品、关键物品的设定，确认后可新增、修改或删除物品。"
      placeholder="例如：设计一件都市恋爱里能推动误会解除的关键道具。"
      @applied="load"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Pencil, Plus, RefreshCw, RotateCcw, Save, Trash2 } from 'lucide-vue-next'
import ItemList from '../components/ItemList.vue'
import JsonEditor from '../components/JsonEditor.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { listCharacters } from '../api/characters'
import { createInventoryRecord } from '../api/inventory'
import { createItem, deleteItem, listItems, updateItem } from '../api/items'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { itemStateLabels, optionsFrom, ownerTypeLabels, rarityLabels } from '../utils/labels'

const gameStore = useGameStore()
const ui = useUiStore()
defineProps({
  embedded: { type: Boolean, default: false }
})
const items = ref([])
const characters = ref([])
const filters = reactive({ q: '', type: '', keyOnly: false, consumableOnly: false, equippableOnly: false })
const itemStateOptions = optionsFrom(itemStateLabels)
const rarityOptions = optionsFrom(rarityLabels)
const ownerTypeOptions = optionsFrom(ownerTypeLabels).filter((option) => option.value !== 'unknown')
const blank = () => ({
  id: null,
  name: '',
  item_type: '普通物品',
  description: '',
  status: 'normal',
  rarity: 'common',
  quantity_limit: 99,
  is_stackable: true,
  is_equippable: false,
  is_consumable: false,
  is_key_item: false,
  is_tradeable: true,
  is_unique: false,
  usable_condition: '',
  effect_description: '',
  current_location: '',
  importance: 5,
  extra_attrs: '{}'
})
const form = reactive(blank())
const assignment = reactive({ item_id: null, owner_type: 'character', owner_id: null, owner_name: '', quantity: 1 })
const filteredItems = computed(() => items.value.filter((item) => {
  if (filters.q && !item.name.includes(filters.q)) return false
  if (filters.type && item.item_type !== filters.type) return false
  if (filters.keyOnly && !item.is_key_item) return false
  if (filters.consumableOnly && !item.is_consumable) return false
  if (filters.equippableOnly && !item.is_equippable) return false
  return true
}))

function reset() {
  Object.assign(form, blank())
}

function edit(item) {
  Object.assign(form, item)
  assignment.item_id = item.id
}

function syncOwnerName() {
  const character = characters.value.find((item) => item.id === assignment.owner_id)
  if (character) {
    assignment.owner_type = 'character'
    assignment.owner_name = character.name
  }
}

async function load() {
  await ui.run(async () => {
    if (!gameStore.currentGameId) return
    items.value = await listItems(gameStore.currentGameId)
    characters.value = await listCharacters(gameStore.currentGameId)
    if (!assignment.item_id && items.value[0]) assignment.item_id = items.value[0].id
  })
}

async function save() {
  const data = { ...form }
  delete data.id
  await ui.run(async () => {
    if (form.id) await updateItem(form.id, data)
    else await createItem(gameStore.currentGameId, data)
    reset()
    await load()
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteItem(id)
    reset()
    await load()
  })
}

async function assign() {
  await ui.run(async () => {
    await createInventoryRecord(gameStore.currentGameId, { ...assignment, owner_id: assignment.owner_id || null })
  })
}

onMounted(load)
</script>
