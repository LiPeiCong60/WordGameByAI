<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>名称</th>
          <th>类型</th>
          <th>稀有度</th>
          <th>状态</th>
          <th>属性</th>
          <th v-if="$slots.actions">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td><strong>{{ item.name }}</strong><small>{{ item.description }}</small></td>
          <td>{{ item.item_type }}</td>
          <td>{{ labelFor(rarityLabels, item.rarity) }}</td>
          <td>{{ labelFor(itemStateLabels, item.status) }}</td>
          <td class="tag-cell">
            <span v-if="item.is_equippable">装备</span>
            <span v-if="item.is_consumable">消耗</span>
            <span v-if="item.is_key_item">关键</span>
          </td>
          <td v-if="$slots.actions"><slot name="actions" :item="item" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { itemStateLabels, labelFor, rarityLabels } from '../utils/labels'

defineProps({
  items: { type: Array, default: () => [] }
})
</script>
