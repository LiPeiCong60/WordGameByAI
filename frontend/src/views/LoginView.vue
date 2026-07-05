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
        <div class="captcha-row">
          <button type="button" class="captcha-image" title="刷新验证码" @click="loadCaptcha" v-html="captcha.svg" />
          <label class="field captcha-answer"><span>验证码</span><input v-model.trim="form.captcha_answer" required inputmode="numeric" autocomplete="off" /></label>
        </div>
        <button type="submit" class="primary" :disabled="ui.loading">登录</button>
      </form>
      <p class="auth-switch">还没有账号？<RouterLink to="/register">注册</RouterLink></p>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { getCaptcha } from '../api/auth'
import { useAuthStore } from '../stores/authStore'
import { useUiStore } from '../stores/uiStore'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()
const captcha = reactive({ captcha_id: '', svg: '' })
const form = reactive({ username: '', password: '', captcha_answer: '' })

async function loadCaptcha() {
  const data = await getCaptcha()
  captcha.captcha_id = data.captcha_id
  captcha.svg = data.svg
  form.captcha_answer = ''
}

async function submit() {
  await ui.run(async () => {
    await auth.login({ ...form, captcha_id: captcha.captcha_id })
    router.push(route.query.redirect || '/management')
  }).catch(loadCaptcha)
}

onMounted(loadCaptcha)
</script>
