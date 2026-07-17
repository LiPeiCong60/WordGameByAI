import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const GameListView = () => import('../views/GameListView.vue')
const GamePlayView = () => import('../views/GamePlayView.vue')
const AdminView = () => import('../views/AdminView.vue')
const LoginView = () => import('../views/LoginView.vue')
const TemplateView = () => import('../views/TemplateView.vue')
const ManagementView = () => import('../views/ManagementView.vue')
const RegisterView = () => import('../views/RegisterView.vue')

const routes = [
  { path: '/', redirect: '/management' },
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/register', component: RegisterView, meta: { public: true } },
  { path: '/saves', component: GameListView },
  { path: '/play', component: GamePlayView },
  { path: '/games/:gameId/play', component: GamePlayView },
  { path: '/admin', component: AdminView, meta: { admin: true } },
  { path: '/characters', redirect: { path: '/management', query: { tab: 'characters' } } },
  { path: '/lore', redirect: { path: '/management', query: { tab: 'lore' } } },
  { path: '/worlds', redirect: { path: '/management', query: { tab: 'worlds' } } },
  { path: '/templates', component: TemplateView },
  { path: '/management', component: ManagementView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.isAuthenticated && (to.path === '/login' || to.path === '/register')) return '/management'
    return true
  }
  if (!auth.isAuthenticated) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.meta.admin && !auth.isAdmin) return '/management'
  return true
})

export default router
