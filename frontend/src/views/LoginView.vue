<template>
  <section class="auth-page">
    <div class="auth-visual" aria-hidden="true">
      <div class="auth-brand-lockup">
        <img src="/assets/brand/app_icon.webp" alt="" />
        <div><strong>World Game</strong><span>by AI</span></div>
      </div>
      <div class="auth-visual-copy">
        <span class="eyebrow">AI INTERACTIVE STORY</span>
        <h1>每一次选择，<br />都让世界继续生长。</h1>
        <p>创建角色、探索世界，与 AI 一起写下只属于你的故事。</p>
      </div>
      <div class="auth-cast">
        <img src="/assets/avatars/young_man_refined.webp" alt="" />
        <img src="/assets/avatars/young_woman_elegant.webp" alt="" />
        <img src="/assets/avatars/teen_girl_lively.webp" alt="" />
      </div>
      <div class="auth-feature-row">
        <span><Sparkles :size="16" />自由剧情</span>
        <span><UsersRound :size="16" />鲜活角色</span>
        <span><BookOpen :size="16" />无限世界</span>
      </div>
    </div>
    <div class="auth-panel">
      <header class="auth-panel-header">
        <span class="auth-mini-logo"><img src="/assets/brand/app_icon.webp" alt="" /></span>
        <div>
          <span class="eyebrow">欢迎回来</span>
          <h1>继续你的故事</h1>
        </div>
      </header>
      <form class="form-grid" @submit.prevent="submit">
        <label class="field wide"><span>用户名</span><input v-model.trim="form.username" required autocomplete="username" placeholder="请输入用户名" /></label>
        <label class="field wide"><span>密码</span><input v-model="form.password" required type="password" autocomplete="current-password" placeholder="请输入密码" /></label>
        <div class="captcha-row">
          <button type="button" class="captcha-image" title="刷新验证码" @click="loadCaptcha">
            <img v-if="captchaImageSrc" :src="captchaImageSrc" alt="验证码" />
          </button>
          <label class="field captcha-answer"><span>验证码</span><input v-model.trim="form.captcha_answer" required inputmode="numeric" autocomplete="off" placeholder="答案" /></label>
        </div>
        <button type="submit" class="primary auth-submit" :disabled="ui.loading">
          <span>{{ ui.loading ? '登录中…' : '进入故事世界' }}</span><ArrowRight :size="18" />
        </button>
      </form>
      <p class="auth-switch">还没有账号？<RouterLink to="/register">注册</RouterLink></p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowRight, BookOpen, Sparkles, UsersRound } from 'lucide-vue-next'
import { getCaptcha } from '../api/auth'
import { useAuthStore } from '../stores/authStore'
import { useUiStore } from '../stores/uiStore'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()
const captcha = reactive({ captcha_id: '', svg: '' })
const form = reactive({ username: '', password: '', captcha_answer: '' })
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
    await auth.login({ ...form, captcha_id: captcha.captcha_id })
    router.push(route.query.redirect || '/management')
  }).catch(loadCaptcha)
}

onMounted(loadCaptcha)
</script>
