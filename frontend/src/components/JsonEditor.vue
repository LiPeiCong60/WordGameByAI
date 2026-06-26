<template>
  <label class="field json-field">
    <span>{{ label }}</span>
    <textarea :value="modelValue" rows="6" spellcheck="false" @input="$emit('update:modelValue', $event.target.value)" />
  </label>
</template>

<script setup>
defineProps({
  label: { type: String, default: '扩展属性 JSON' },
  modelValue: { type: String, default: '{}' }
})
defineEmits(['update:modelValue'])
</script>
