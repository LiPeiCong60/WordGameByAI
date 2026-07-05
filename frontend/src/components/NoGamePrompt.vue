<template>
  <section class="empty-state">
    <div>
      <span class="step-badge">先做这一步</span>
      <h1>请选择或创建一个存档</h1>
      <p>角色、世界观和剧情状态都会保存在当前存档里。先进入一个存档，再管理对应板块。</p>
    </div>
    <RouterLink class="primary-link" to="/">
      <Gamepad2 :size="18" />
      去存档页
    </RouterLink>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { Gamepad2 } from 'lucide-vue-next'
</script>
