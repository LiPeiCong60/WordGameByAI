<template>
  <section class="auth-page">
    <div class="auth-visual auth-visual-register" aria-hidden="true">
      <div class="auth-brand-lockup">
        <img src="/assets/brand/app_icon.webp" alt="" />
        <div><strong>World Game</strong><span>by AI</span></div>
      </div>
      <div class="auth-visual-copy">
        <span class="eyebrow">CREATE YOUR UNIVERSE</span>
        <h1>从一个角色开始，<br />创造你的完整世界。</h1>
        <p>所有存档云端同步，网页端与 Android 端共享同一段冒险。</p>
      </div>
      <div class="auth-cast">
        <img src="/assets/avatars/young_woman_approachable.webp" alt="" />
        <img src="/assets/avatars/young_man_rugged.webp" alt="" />
        <img src="/assets/avatars/middle_woman_capable.webp" alt="" />
      </div>
      <div class="auth-feature-row">
        <span><Sparkles :size="16" />AI 共创</span>
        <span><Cloud :size="16" />云端存档</span>
        <span><ShieldCheck :size="16" />安全访问</span>
      </div>
    </div>
    <div class="auth-panel">
      <header class="auth-panel-header">
        <span class="auth-mini-logo"><img src="/assets/brand/app_icon.webp" alt="" /></span>
        <div>
          <span class="eyebrow">创建账号</span>
          <h1>开启新的故事</h1>
        </div>
      </header>
      <form class="form-grid" @submit.prevent="submit">
        <label class="field"><span>用户名</span><input v-model.trim="form.username" required autocomplete="username" placeholder="用于登录和显示" /></label>
        <label class="field"><span>邮箱，可选</span><input v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.com" /></label>
        <label class="field wide"><span>密码</span><input v-model="form.password" required minlength="8" type="password" autocomplete="new-password" placeholder="至少 8 位字符" /></label>
        <label class="field wide"><span>初始管理员令牌，仅首次部署时填写</span><input v-model="form.bootstrap_token" type="password" autocomplete="off" placeholder="普通用户请留空" /></label>
        <div class="captcha-row">
          <button type="button" class="captcha-image" title="刷新验证码" @click="loadCaptcha">
            <img v-if="captchaImageSrc" :src="captchaImageSrc" alt="验证码" />
          </button>
          <label class="field captcha-answer"><span>验证码</span><input v-model.trim="form.captcha_answer" required inputmode="numeric" autocomplete="off" /></label>
        </div>
        <button type="submit" class="primary auth-submit" :disabled="ui.loading">
          <span>{{ ui.loading ? '创建中…' : '创建账号并进入' }}</span><ArrowRight :size="18" />
        </button>
      </form>
      <p class="auth-switch">已有账号？<RouterLink to="/login">登录</RouterLink></p>
      <p class="muted-text">管理员账号需要使用服务器配置的初始管理员令牌创建；普通注册无需填写。</p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, Cloud, ShieldCheck, Sparkles } from 'lucide-vue-next'
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
  bootstrap_token: '',
  captcha_answer: ''
})
const captchaImageSrc = computed(() => (
  captcha.svg ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(captcha.svg)}` : ''
))

async function loadCaptcha() {
  try {
    const data = await getCaptcha()
    captcha.captcha_id = data.captcha_id
    captcha.svg = data.svg
    form.captcha_answer = ''
  } catch (error) {
    ui.setError(error)
  }
}

async function submit() {
  await ui.run(async () => {
    await auth.register({ ...form, captcha_id: captcha.captcha_id })
    router.push('/management')
  }).catch(loadCaptcha)
}

onMounted(loadCaptcha)
</script>
