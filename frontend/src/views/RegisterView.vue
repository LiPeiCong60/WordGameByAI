<template>
  <section class="auth-page">
    <div class="auth-panel">
      <header>
        <span class="brand-mark">NA</span>
        <h1>注册账号</h1>
      </header>
      <form class="form-grid" @submit.prevent="submit">
        <label class="field"><span>用户名</span><input v-model.trim="form.username" required autocomplete="username" /></label>
        <label class="field"><span>邮箱，可选</span><input v-model.trim="form.email" type="email" autocomplete="email" /></label>
        <label class="field"><span>密码</span><input v-model="form.password" required minlength="8" type="password" autocomplete="new-password" /></label>
        <div class="captcha-row">
          <button type="button" class="captcha-image" title="刷新验证码" @click="loadCaptcha">
            <img v-if="captchaImageSrc" :src="captchaImageSrc" alt="验证码" />
          </button>
          <label class="field captcha-answer"><span>验证码</span><input v-model.trim="form.captcha_answer" required inputmode="numeric" autocomplete="off" /></label>
        </div>
        <button type="submit" class="primary" :disabled="ui.loading">注册并登录</button>
      </form>
      <p class="auth-switch">已有账号？<RouterLink to="/login">登录</RouterLink></p>
      <p class="muted-text">第一个注册用户会自动成为管理员。</p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { getCaptcha } from '../api/auth'
import { useAuthStore } from '../stores/authStore'
import { useUiStore } from '../stores/uiStore'

const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()
const captcha = reactive({ captcha_id: '', svg: '' })
const form = reactive({
  username: '',
  email: '',
  password: '',
  captcha_answer: ''
})
const captchaImageSrc = computed(() => (
  captcha.svg ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(captcha.svg)}` : ''
))

async function loadCaptcha() {
  const data = await getCaptcha()
  captcha.captcha_id = data.captcha_id
  captcha.svg = data.svg
  form.captcha_answer = ''
}

async function submit() {
  await ui.run(async () => {
    await auth.register({ ...form, captcha_id: captcha.captcha_id })
    router.push('/management')
  }).catch(loadCaptcha)
}

onMounted(loadCaptcha)
</script>
