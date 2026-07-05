<template>
  <section class="auth-page">
    <div class="auth-panel">
      <header>
        <span class="brand-mark">NA</span>
        <h1>登录 NarrativeAgent</h1>
      </header>
      <form class="form-grid" @submit.prevent="submit">
        <label class="field"><span>用户名</span><input v-model.trim="form.username" required autocomplete="username" /></label>
        <label class="field"><span>密码</span><input v-model="form.password" required type="password" autocomplete="current-password" /></label>
        <button type="submit" class="primary" :disabled="ui.loading">登录</button>
      </form>
      <p class="auth-switch">还没有账号？<RouterLink to="/register">注册</RouterLink></p>
    </div>
  </section>
</template>

<script setup>
import { reactive } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useUiStore } from '../stores/uiStore'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()
const form = reactive({ username: '', password: '' })

async function submit() {
  await ui.run(async () => {
    await auth.login(form)
    router.push(route.query.redirect || '/management')
  })
}
</script>
