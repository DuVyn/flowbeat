/**
 * main.ts — 应用入口
 *
 * 职责：
 * 1. 创建 Vue 应用实例
 * 2. 注册 Pinia 状态管理
 * 3. 注册 Vue Router 路由
 * 4. 导入全局样式
 * 5. 挂载到 DOM
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

// 全局样式（设计变量与重置样式）
import '@/assets/styles/main.css'

/* ---- 创建应用实例 ---- */
const app = createApp(App)

/* ---- 注册插件 ---- */
// Pinia 状态管理（必须在 Router 之前注册，以便路由守卫中可使用 store）
app.use(createPinia())
// Vue Router
app.use(router)

/* ---- 挂载到 #app ---- */
app.mount('#app')
