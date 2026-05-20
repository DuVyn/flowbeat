<script setup lang="ts">
/**
 * MainLayout — 主框架布局
 *
 * 视觉设计：三张圆角卡片浮在浅色背景上
 *
 *   ┌─────────────────────────────────────────┐
 *   │ (浅绿背景 + 间隙)                         │
 *   │  ╭──────────╮  ╭────────────────────╮   │
 *   │  │          │  │ [←][→] [搜索] [👤] │   │
 *   │  │  侧边栏   │  │                    │   │
 *   │  │  (卡片)   │  │  主内容区 (卡片)     │   │
 *   │  │          │  │                    │   │
 *   │  │  全高     │  ╰────────────────────╯   │
 *   │  │          │  ╭────────────────────╮   │
 *   │  │          │  │  播放器 (卡片)       │   │
 *   │  ╰──────────╯  ╰────────────────────╯   │
 *   └─────────────────────────────────────────┘
 *
 * CSS Grid 布局：侧边栏 span 全行，右侧分上下两格。
 */

import TheSidebar from '@/components/navigation/TheSidebar.vue'
import TheTopBar from '@/components/navigation/TheTopBar.vue'
import ThePlayer from '@/components/player/ThePlayer.vue'
import GenrePreferenceModal from '@/components/common/GenrePreferenceModal.vue'
</script>

<template>
  <div class="main-layout">
    <!-- 侧边栏卡片（占满全高） -->
    <div class="main-layout__card main-layout__card--sidebar">
      <TheSidebar />
    </div>

    <!-- 主内容卡片 -->
    <div class="main-layout__card main-layout__card--content">
      <!-- 顶部导航区域（固定在内容区顶部） -->
      <TheTopBar class="main-layout__topbar" />
      <!-- 可滚动的页面内容 -->
      <main class="main-layout__scroll">
        <RouterView />
      </main>
    </div>

    <!-- 播放器卡片 -->
    <div class="main-layout__card main-layout__card--player">
      <ThePlayer />
    </div>
  </div>

  <GenrePreferenceModal />
</template>

<style scoped>
/* ========================================
 * 布局根容器 — 浅色背景
 * ======================================== */
.main-layout {
  --sidebar-width: 232px;
  --player-height: 80px;
  --layout-gap: 8px;
  --card-radius: var(--radius-xl);
  --card-bg: var(--surface-0);
  --card-border: var(--surface-border);
  --card-shadow: var(--shadow-soft);

  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: 1fr var(--player-height);
  grid-template-areas:
    'sidebar content'
    'sidebar player';
  gap: var(--layout-gap);
  padding: var(--layout-gap);
  height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(31, 122, 93, 0.06), transparent 45%),
    linear-gradient(180deg, var(--surface-1) 0%, var(--surface-2) 100%);
  color: var(--ink-900);
  overflow: hidden;
}

/* ========================================
 * 通用卡片样式
 * ======================================== */
.main-layout__card {
  border-radius: var(--card-radius);
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  overflow: hidden;
  box-shadow: var(--card-shadow);
  min-width: 0;
}

/* ---- 侧边栏卡片（跨两行） ---- */
.main-layout__card--sidebar {
  grid-area: sidebar;
}

/* ---- 内容卡片 ---- */
.main-layout__card--content {
  grid-area: content;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许 flex 子项收缩 */
  overflow: visible; /* 允许顶部下拉菜单溢出显示 */
}

/* ---- 播放器卡片 ---- */
.main-layout__card--player {
  grid-area: player;
}

/* ========================================
 * 顶部导航（粘性定位在内容顶部）
 * ======================================== */
.main-layout__topbar {
  flex-shrink: 0;
}

/* ========================================
 * 可滚动内容区域
 * ======================================== */
.main-layout__scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1.25rem 1.5rem 1.5rem;
  min-width: 0;
  scrollbar-color: rgba(15, 23, 42, 0.28) transparent;

  /* 自定义滚动条 */
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(15, 23, 42, 0.18);
    border-radius: 3px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(15, 23, 42, 0.28);
  }
}

/* ========================================
 * 响应式：移动端 (< 768px)
 * ======================================== */
@media (max-width: 768px) {
  .main-layout {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr var(--player-height);
    grid-template-areas:
      'content'
      'player';
  }

  .main-layout__card--sidebar {
    display: none;
  }
}
</style>
