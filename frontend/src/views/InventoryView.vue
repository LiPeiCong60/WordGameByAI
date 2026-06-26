<template>
  <SaveContextBar v-if="!embedded" @changed="load" />
  <NoGamePrompt v-if="!gameStore.currentGameId" />
  <section v-else class="view-grid two">
    <div class="panel">
      <header class="panel-header">
        <h1>库存</h1>
        <button type="button" class="icon-button" title="刷新" @click="load"><RefreshCw :size="17" /></button>
      </header>
      <div class="filters">
        <input v-model="filters.owner" placeholder="拥有者" />
        <input v-model="filters.item" placeholder="物品名" />
        <select v-model="filters.ownerType">
          <option value="">全部类型</option>
          <option v-for="option in ownerTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>
      <InventoryPanel :records="filteredRecords" :items="items">
        <template #actions="{ record }">
          <button type="button" @click="edit(record)"><Pencil :size="17" /></button>
        </template>
      </InventoryPanel>
    </div>
    <div class="panel">
      <header class="panel-header"><h1>{{ form.id ? '编辑库存' : '新增库存' }}</h1></header>
      <form class="form-grid" @submit.prevent="save">
        <label class="field"><span>物品</span><select v-model.number="form.item_id"><option v-for="item in items" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
        <label class="field"><span>拥有者类型</span><select v-model="form.owner_type"><option v-for="option in ownerTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
        <label class="field"><span>角色</span><select v-model.number="form.owner_id" @change="syncOwnerName"><option :value="null">非角色</option><option v-for="character in characters" :key="character.id" :value="character.id">{{ character.name }}</option></select></label>
        <label class="field"><span>拥有者名称</span><input v-model="form.owner_name" /></label>
        <label class="field"><span>数量</span><input v-model.number="form.quantity" type="number" /></label>
        <label class="field"><span>存放位置</span><input v-model="form.storage_location" /></label>
        <label class="field"><span>状态</span><select v-model="form.item_state"><option v-for="option in itemStateOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
        <label class="check-field"><input v-model="form.equipped" type="checkbox" />已装备</label>
        <label class="field wide"><span>备注</span><textarea v-model="form.note" rows="3" /></label>
        <button type="submit" class="primary"><Save :size="17" />保存</button>
        <button type="button" @click="reset"><RotateCcw :size="17" />重置</button>
        <button v-if="form.id" type="button" @click="remove(form.id)"><Trash2 :size="17" />删除</button>
      </form>
      <div class="sub-panel">
        <h2>强校验操作</h2>
        <div class="button-row">
          <button type="button" @click="useSelected"><Zap :size="17" />使用</button>
          <button type="button" @click="equipSelected"><ShieldCheck :size="17" />装备</button>
          <button type="button" @click="unequipSelected"><ShieldOff :size="17" />卸下</button>
        </div>
        <form class="form-grid" @submit.prevent="transferSelected">
          <label class="field"><span>转给类型</span><select v-model="transfer.to_owner_type"><option v-for="option in ownerTypeOptions.filter((item) => item.value !== 'unknown')" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
          <label class="field"><span>转给角色</span><select v-model.number="transfer.to_owner_id" @change="syncTransferName"><option :value="null">非角色</option><option v-for="character in characters" :key="character.id" :value="character.id">{{ character.name }}</option></select></label>
          <label class="field"><span>转给名称</span><input v-model="transfer.to_owner_name" /></label>
          <label class="field"><span>数量</span><input v-model.number="transfer.quantity" type="number" min="1" /></label>
          <button type="submit" class="primary"><ArrowRightLeft :size="17" />转移</button>
        </form>
      </div>
    </div>
    <SectionAgentPanel
      v-if="!embedded"
      scope="库存"
      title="库存智能体"
      description="讨论物品归属、数量、装备、转移、消耗等库存变化，确认后写入库存。"
      placeholder="例如：把旧钥匙转给当前同伴，并把主角的补给数量减 1。"
      @applied="load"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowRightLeft, Pencil, RefreshCw, RotateCcw, Save, ShieldCheck, ShieldOff, Trash2, Zap } from 'lucide-vue-next'
import InventoryPanel from '../components/InventoryPanel.vue'
import NoGamePrompt from '../components/NoGamePrompt.vue'
import SaveContextBar from '../components/SaveContextBar.vue'
import SectionAgentPanel from '../components/SectionAgentPanel.vue'
import { listCharacters } from '../api/characters'
import { createInventoryRecord, deleteInventoryRecord, equipItem, listInventory, transferItem, unequipItem, updateInventoryRecord, useItem } from '../api/inventory'
import { listItems } from '../api/items'
import { useGameStore } from '../stores/gameStore'
import { useUiStore } from '../stores/uiStore'
import { itemStateLabels, optionsFrom, ownerTypeLabels } from '../utils/labels'

const gameStore = useGameStore()
const ui = useUiStore()
defineProps({
  embedded: { type: Boolean, default: false }
})
const records = ref([])
const items = ref([])
const characters = ref([])
const filters = reactive({ owner: '', item: '', ownerType: '' })
const ownerTypeOptions = optionsFrom(ownerTypeLabels)
const itemStateOptions = optionsFrom(itemStateLabels)
const blank = () => ({ id: null, item_id: null, owner_type: 'character', owner_id: null, owner_name: '', quantity: 1, equipped: false, storage_location: '', item_state: 'normal', note: '' })
const form = reactive(blank())
const transfer = reactive({ to_owner_type: 'character', to_owner_id: null, to_owner_name: '', quantity: 1 })

const filteredRecords = computed(() => records.value.filter((record) => {
  const itemName = items.value.find((item) => item.id === record.item_id)?.name || ''
  if (filters.owner && !(record.owner_name || '').includes(filters.owner)) return false
  if (filters.item && !itemName.includes(filters.item)) return false
  if (filters.ownerType && record.owner_type !== filters.ownerType) return false
  return true
}))

function reset() {
  Object.assign(form, blank())
}

function edit(record) {
  Object.assign(form, record)
}

function syncOwnerName() {
  const character = characters.value.find((item) => item.id === form.owner_id)
  if (character) {
    form.owner_type = 'character'
    form.owner_name = character.name
  }
}

function syncTransferName() {
  const character = characters.value.find((item) => item.id === transfer.to_owner_id)
  if (character) {
    transfer.to_owner_type = 'character'
    transfer.to_owner_name = character.name
  }
}

async function load() {
  await ui.run(async () => {
    if (!gameStore.currentGameId) return
    records.value = await listInventory(gameStore.currentGameId)
    items.value = await listItems(gameStore.currentGameId)
    characters.value = await listCharacters(gameStore.currentGameId)
    if (!form.item_id && items.value[0]) form.item_id = items.value[0].id
  })
}

async function save() {
  const data = { ...form, owner_id: form.owner_id || null }
  delete data.id
  await ui.run(async () => {
    if (form.id) await updateInventoryRecord(form.id, data)
    else await createInventoryRecord(gameStore.currentGameId, data)
    reset()
    await load()
  })
}

async function remove(id) {
  await ui.run(async () => {
    await deleteInventoryRecord(id)
    reset()
    await load()
  })
}

async function useSelected() {
  if (!form.owner_id || !form.item_id) return
  await ui.run(async () => {
    await useItem({ game_id: gameStore.currentGameId, character_id: form.owner_id, item_id: form.item_id, quantity: 1, context: '前端库存操作' })
    await load()
  })
}

async function equipSelected() {
  if (!form.owner_id || !form.item_id) return
  await ui.run(async () => {
    await equipItem({ game_id: gameStore.currentGameId, character_id: form.owner_id, item_id: form.item_id })
    await load()
  })
}

async function unequipSelected() {
  if (!form.owner_id || !form.item_id) return
  await ui.run(async () => {
    await unequipItem({ game_id: gameStore.currentGameId, character_id: form.owner_id, item_id: form.item_id })
    await load()
  })
}

async function transferSelected() {
  if (!form.item_id) return
  await ui.run(async () => {
    await transferItem({
      game_id: gameStore.currentGameId,
      item_id: form.item_id,
      from_owner_type: form.owner_type,
      from_owner_id: form.owner_id || null,
      from_owner_name: form.owner_name,
      to_owner_type: transfer.to_owner_type,
      to_owner_id: transfer.to_owner_id || null,
      to_owner_name: transfer.to_owner_name,
      quantity: transfer.quantity
    })
    await load()
  })
}

onMounted(load)
</script>
