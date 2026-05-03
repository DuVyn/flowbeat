<script setup lang="ts">
/**
 * TheSidebar — 左侧导航栏
 *
 * 包含：
 *   1. 品牌标识（FlowBeat Logo）
 *   2. 主导航菜单（首页、发现音乐、个性推荐、历史播放等）
 *   3. 后续可扩展：用户歌单列表、收藏夹等
 *
 * 当前路由自动高亮对应导航项（通过 RouterLink 的 exact-active 状态）。
 */

/* ---- 导航菜单配置 ---- */
interface NavItem {
  name: string // 显示文字
  icon: string // SVG path（使用 24x24 viewBox）
  to: string // 路由路径
}

const navItems: NavItem[] = [
  {
    name: '首页',
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1',
    to: '/',
  },
  {
    name: '发现音乐',
    icon: 'M21 12a9 9 0 11-18 0 9 9 0 0118 0z M15.91 11.672a.375.375 0 010 .656l-5.603 3.113a.375.375 0 01-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112z',
    to: '/discover',
  },
  {
    name: '个性推荐',
    icon: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z',
    to: '/recommend',
  },
]

/* ---- 我的音乐（第二组导航） ---- */
const myMusicItems: NavItem[] = [
  {
    name: '我喜欢',
    icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
    to: '/favorites',
  },
  {
    name: '历史播放',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    to: '/history',
  },
]
</script>

<template>
  <aside class="sidebar">
    <!-- 品牌标识 -->
    <div class="sidebar__brand">
      <div class="sidebar__brand-icon">
        <!-- 音符图标 -->
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
        </svg>
      </div>
      <span class="sidebar__brand-name">FlowBeat</span>
    </div>

    <!-- 主导航 -->
    <nav class="sidebar__nav">
      <p class="sidebar__nav-label">浏览</p>
      <ul class="sidebar__nav-list">
        <li v-for="item in navItems" :key="item.to">
          <RouterLink
            :to="item.to"
            class="sidebar__nav-link"
            exact-active-class="sidebar__nav-link--active"
          >
            <svg
              class="sidebar__nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path :d="item.icon" />
            </svg>
            <span>{{ item.name }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>

    <!-- 分割线 -->
    <div class="sidebar__divider"></div>

    <!-- 我的音乐 -->
    <nav class="sidebar__nav">
      <p class="sidebar__nav-label">我的音乐</p>
      <ul class="sidebar__nav-list">
        <li v-for="item in myMusicItems" :key="item.to">
          <RouterLink
            :to="item.to"
            class="sidebar__nav-link"
            exact-active-class="sidebar__nav-link--active"
          >
            <svg
              class="sidebar__nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path :d="item.icon" />
            </svg>
            <span>{{ item.name }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>
  </aside>
</template>

<style scoped>
/* ========================================
 * 侧边栏容器
 * ======================================== */
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0 0.75rem;
  background-color: #ffffff;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  overflow-y: auto;

  /* 隐藏滚动条 */
  scrollbar-width: none;
  &::-webkit-scrollbar {
    display: none;
  }
}

/* ========================================
 * 品牌标识
 * ======================================== */
.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 1.125rem 0.75rem;
  margin-bottom: 0.5rem;
}

.sidebar__brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4caf7d 0%, #3d9e6e 100%);
  color: #ffffff;
  flex-shrink: 0;
}

.sidebar__brand-icon svg {
  width: 18px;
  height: 18px;
}

.sidebar__brand-name {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #1a2e1a 30%, #4caf7d);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* ========================================
 * 导航区块
 * ======================================== */
.sidebar__nav {
  padding: 0 0.25rem;
}

.sidebar__nav-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(0, 0, 0, 0.35);
  padding: 0.5rem 0.75rem 0.375rem;
  margin: 0;
}

.sidebar__nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* ========================================
 * 导航链接
 * ======================================== */
.sidebar__nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 450;
  color: rgba(0, 0, 0, 0.5);
  text-decoration: none;
  transition: all 0.2s ease;
}

.sidebar__nav-link:hover {
  color: rgba(0, 0, 0, 0.8);
  background: rgba(76, 175, 125, 0.08);
}

/* 激活状态 */
.sidebar__nav-link--active {
  color: #1a2e1a;
  background: rgba(76, 175, 125, 0.12);
}

.sidebar__nav-link--active .sidebar__nav-icon {
  color: #4caf7d;
}

.sidebar__nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  transition: color 0.2s ease;
}

/* ========================================
 * 分割线
 * ======================================== */
.sidebar__divider {
  height: 1px;
  margin: 0.75rem 1rem;
  background: rgba(0, 0, 0, 0.08);
}
</style>
