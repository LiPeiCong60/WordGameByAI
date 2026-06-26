<template>
  <details v-if="collapsible" class="panel collapsible-panel" open>
    <summary class="panel-header collapsible-summary">
      <h2>{{ title }}</h2>
      <span>{{ records.length }}</span>
      <ChevronDown class="collapsible-icon" :size="17" />
    </summary>
    <div class="table-wrap compact">
      <table>
        <thead>
          <tr>
            <th>物品</th>
            <th>拥有者</th>
            <th>数量</th>
            <th>状态</th>
            <th>装备</th>
            <th v-if="$slots.actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td>{{ itemName(record.item_id) }}</td>
            <td>{{ record.owner_name || labelFor(ownerTypeLabels, record.owner_type) }}</td>
            <td>{{ record.quantity }}</td>
            <td>{{ labelFor(itemStateLabels, record.item_state) }}</td>
            <td>{{ record.equipped ? '是' : '否' }}</td>
            <td v-if="$slots.actions"><slot name="actions" :record="record" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </details>
  <section v-else class="panel">
    <header class="panel-header">
      <h2>{{ title }}</h2>
      <span>{{ records.length }}</span>
    </header>
    <div class="table-wrap compact">
      <table>
        <thead>
          <tr>
            <th>物品</th>
            <th>拥有者</th>
            <th>数量</th>
            <th>状态</th>
            <th>装备</th>
            <th v-if="$slots.actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td>{{ itemName(record.item_id) }}</td>
            <td>{{ record.owner_name || labelFor(ownerTypeLabels, record.owner_type) }}</td>
            <td>{{ record.quantity }}</td>
            <td>{{ labelFor(itemStateLabels, record.item_state) }}</td>
            <td>{{ record.equipped ? '是' : '否' }}</td>
            <td v-if="$slots.actions"><slot name="actions" :record="record" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { ChevronDown } from 'lucide-vue-next'
import { itemStateLabels, labelFor, ownerTypeLabels } from '../utils/labels'

const props = defineProps({
  title: { type: String, default: '库存' },
  records: { type: Array, default: () => [] },
  items: { type: Array, default: () => [] },
  collapsible: { type: Boolean, default: false }
})

function itemName(id) {
  return props.items.find((item) => item.id === id)?.name || `#${id}`
}
</script>
