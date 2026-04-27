<script setup lang="ts">
/**
 * TheTopBar — 内容区顶部导航
 *
 * 不再作为独立顶栏，而是嵌入内容卡片顶部。
 * 包含：
 *   1. 搜索框
 *   2. 用户头像与个人中心入口（含下拉菜单）
 */

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { logout } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
authStore.hydrateFromStorage()

const userAvatarText = computed(() => {
  const username = authStore.user?.username?.trim()
  if (!username) {
    return 'U'
  }
  return username.slice(0, 1).toUpperCase()
})

/* ---- 搜索 ---- */
const searchQuery = ref('')

function readSearchQueryFromRoute(): string {
  const rawQuery = route.query.q
  if (Array.isArray(rawQuery)) {
    return String(rawQuery[0] ?? '').trim()
  }
  return typeof rawQuery === 'string' ? rawQuery.trim() : ''
}

function syncSearchInputFromRoute(): void {
  if (route.name !== 'Search') {
    return
  }
  searchQuery.value = readSearchQueryFromRoute()
}

function handleSearch() {
  const query = searchQuery.value.trim()
  if (!query) return
  void router.push({
    name: 'Search',
    query: { q: query },
  })
}

watch(
  () => [route.name, route.query.q],
  () => {
    syncSearchInputFromRoute()
  },
  { immediate: true },
)

/* ---- 用户下拉菜单 ---- */
const showUserMenu = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

/** 点击外部关闭菜单 */
function handleClickOutside(e: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target as Node)) {
    showUserMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside, true)
})

/** 个人中心 */
function goToProfile() {
  showUserMenu.value = false
  router.push('/profile')
}

/** 退出登录 */
async function handleLogout() {
  showUserMenu.value = false
  try {
    await logout()
  } catch {
    // 即使接口失败也要清理本地登录态，避免用户被卡住。
  }
  authStore.clearSession()
  router.replace('/auth/login')
}
</script>

<template>
  <header class="topbar">
    <!-- 搜索框 -->
    <div class="topbar__search">
      <svg
        class="topbar__search-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        class="topbar__search-input"
        placeholder="搜索歌曲、歌手、歌单..."
        @keydown.enter="handleSearch"
      />
    </div>

    <!-- 用户区域 -->
    <div ref="userMenuRef" class="topbar__user">
      <button class="topbar__avatar" aria-label="用户菜单" @click="toggleUserMenu">
        <span class="topbar__avatar-text">{{ userAvatarText }}</span>
      </button>

      <!-- 下拉菜单 -->
      <Transition name="topbar-dropdown">
        <div v-if="showUserMenu" class="topbar__dropdown">
          <button class="topbar__dropdown-item" @click="goToProfile">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span>个人中心</span>
          </button>
          <div class="topbar__dropdown-divider"></div>
          <button class="topbar__dropdown-item topbar__dropdown-item--danger" @click="handleLogout">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            <span>退出登录</span>
          </button>
        </div>
      </Transition>
    </div>
  </header>
</template>

<style scoped>
/* ========================================
 * 顶栏 — 嵌入内容卡片内部，非独立行
 * ======================================== */
.topbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;

  /* 半透明白色背景 + 底部渐隐，与内容区融为一体 */
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.95) 60%, transparent);
}

/* ========================================
 * 搜索框
 * ======================================== */
.topbar__search {
  flex: 1;
  max-width: 420px;
  position: relative;
  display: flex;
  align-items: center;
}

.topbar__search-icon {
  position: absolute;
  left: 11px;
  width: 15px;
  height: 15px;
  color: rgba(0, 0, 0, 0.3);
  pointer-events: none;
  transition: color 0.2s ease;
}

.topbar__search-input {
  width: 100%;
  padding: 0.45rem 0.75rem 0.45rem 2rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 18px;
  background: rgba(0, 0, 0, 0.03);
  color: #1a2e1a;
  font-size: 0.8125rem;
  font-family: inherit;
  outline: none;
  transition: all 0.25s ease;
}

.topbar__search-input::placeholder {
  color: rgba(0, 0, 0, 0.3);
}

.topbar__search-input:focus {
  background: #ffffff;
  border-color: rgba(76, 175, 125, 0.5);
  box-shadow: 0 0 0 3px rgba(76, 175, 125, 0.1);
}

.topbar__search:focus-within .topbar__search-icon {
  color: rgba(76, 175, 125, 0.8);
}

/* ========================================
 * 用户头像
 * ======================================== */
.topbar__user {
  margin-left: auto;
  flex-shrink: 0;
  position: relative;
}

.topbar__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #4caf7d, #3d9e6e);
  cursor: pointer;
  transition: all 0.2s ease;
}

.topbar__avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 0 14px rgba(76, 175, 125, 0.3);
}

.topbar__avatar-text {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #ffffff;
}

/* ========================================
 * 下拉菜单
 * ======================================== */
.topbar__dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 160px;
  padding: 6px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.1),
    0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 100;
}

.topbar__dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(0, 0, 0, 0.7);
  font-size: 0.8125rem;
  font-weight: 450;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.topbar__dropdown-item:hover {
  background: rgba(76, 175, 125, 0.08);
  color: #1a2e1a;
}

.topbar__dropdown-item svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* 危险操作（退出登录）单独着色 */
.topbar__dropdown-item--danger:hover {
  background: rgba(220, 53, 69, 0.06);
  color: #c0392b;
}

.topbar__dropdown-divider {
  height: 1px;
  margin: 4px 8px;
  background: rgba(0, 0, 0, 0.07);
}

/* ========================================
 * 下拉菜单过渡动画
 * ======================================== */
.topbar-dropdown-enter-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.topbar-dropdown-leave-active {
  transition: all 0.15s ease-in;
}
.topbar-dropdown-enter-from,
.topbar-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.95);
}
</style>
