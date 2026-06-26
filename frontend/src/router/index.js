import { createRouter, createWebHistory } from 'vue-router'
import GameListView from '../views/GameListView.vue'
import GamePlayView from '../views/GamePlayView.vue'
import AdminView from '../views/AdminView.vue'
import TemplateView from '../views/TemplateView.vue'
import ManagementView from '../views/ManagementView.vue'

const routes = [
  { path: '/', redirect: '/management' },
  { path: '/saves', component: GameListView },
  { path: '/play', component: GamePlayView },
  { path: '/games/:gameId/play', component: GamePlayView },
  { path: '/admin', component: AdminView },
  { path: '/characters', redirect: { path: '/management', query: { tab: 'characters' } } },
  { path: '/lore', redirect: { path: '/management', query: { tab: 'lore' } } },
  { path: '/items', redirect: { path: '/management', query: { tab: 'items' } } },
  { path: '/inventory', redirect: { path: '/management', query: { tab: 'inventory' } } },
  { path: '/events', redirect: { path: '/management', query: { tab: 'events' } } },
  { path: '/worlds', redirect: { path: '/management', query: { tab: 'worlds' } } },
  { path: '/templates', component: TemplateView },
  { path: '/management', component: ManagementView }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
