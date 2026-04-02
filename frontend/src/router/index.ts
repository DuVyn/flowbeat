/**
 * router/index.ts — 路由配置
 *
 * 职责：
 * 1. 创建路由实例（HTML5 History 模式）
 * 2. 定义路由表（按布局分组嵌套）
 * 3. 全局前置守卫（登录态校验）
 */

import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

/* ================================================================
 * 布局组件
 * 通过懒加载引入，减少首屏体积
 * ================================================================ */
const MainLayout = () => import('@/layouts/MainLayout.vue')
const AuthLayout = () => import('@/layouts/AuthLayout.vue')

/* ================================================================
 * 路由表
 *
 * 采用「布局嵌套」模式：
 *   App.vue  →  Layout（MainLayout / AuthLayout）  →  Page
 *
 * meta 字段约定：
 *   - requiresAuth: boolean  是否需要登录才能访问（默认 true）
 *   - title: string          页面标题（用于 document.title）
 * ================================================================ */
const routes: RouteRecordRaw[] = [
  /* ---------- 需要登录的主框架页面 ---------- */
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/home/HomePage.vue'),
        meta: { title: '首页', requiresAuth: true },
      },
      // TODO: 后续在此追加 category / search / player 等业务页面
    ],
  },

  /* ---------- 不需要登录的认证页面 ---------- */
  {
    path: '/auth',
    component: AuthLayout,
    children: [
      {
        path: 'login',
        name: 'Login',
        component: () => import('@/views/auth/LoginPage.vue'),
        meta: { title: '登录', requiresAuth: false },
      },
      // TODO: 后续追加注册页 RegisterPage
    ],
  },

  /* ---------- 404 兜底路由（必须放在最后） ---------- */
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/NotFoundPage.vue'),
    meta: { title: '页面未找到', requiresAuth: false },
  },
]

/* ================================================================
 * 创建路由实例
 * ================================================================ */
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,

  // 路由切换后滚动到顶部
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
})

/* ================================================================
 * 全局前置守卫 — 登录态校验
 *
 * 逻辑：
 *   1. 目标路由标记了 requiresAuth 且用户未登录 → 重定向到登录页
 *   2. 用户已登录却访问登录页 → 重定向到首页（防止重复登录）
 *   3. 其余情况正常放行
 *
 * 注意：此处使用 localStorage 中的 token 做简易判断，
 *       后续应替换为 auth store 中的状态 + Token 有效性校验。
 * ================================================================ */
router.beforeEach((to, _from) => {
  // 更新页面标题
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - FlowBeat` : 'FlowBeat'

  /**
   * 简易登录态判断
   * TODO: 替换为 useAuthStore().isAuthenticated
   *       示例：
   *       const authStore = useAuthStore()
   *       const isLoggedIn = authStore.isAuthenticated
   */
  const token = localStorage.getItem('flowbeat_token')
  const isLoggedIn = !!token

  // 目标路由需要登录，但用户未登录 → 跳转登录页，并记录原始目标路径
  if (to.meta.requiresAuth && !isLoggedIn) {
    return {
      name: 'Login',
      query: { redirect: to.fullPath },
    }
  }

  // 已登录用户访问登录页 → 重定向回首页
  if (to.name === 'Login' && isLoggedIn) {
    return { name: 'Home' }
  }

  // 其余情况正常放行
  return true
})

export default router
