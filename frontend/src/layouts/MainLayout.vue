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
</template>

<style scoped>
/* ========================================
 * 布局根容器 — 浅色背景
 * ======================================== */
.main-layout {
  --sidebar-width: 240px;
  --player-height: 72px;
  --layout-gap: 8px;
  --card-radius: 10px;
  --card-bg: #ffffff;

  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: 1fr var(--player-height);
  grid-template-areas:
    "sidebar content"
    "sidebar player";
  gap: var(--layout-gap);
  padding: var(--layout-gap);
  height: 100vh;
  background-color: #e8f0e8;
  color: #1a2e1a;
  overflow: hidden;
}

/* ========================================
 * 通用卡片样式
 * ======================================== */
.main-layout__card {
  border-radius: var(--card-radius);
  background: var(--card-bg);
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
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
  padding: 1.5rem;

  /* 自定义滚动条 */
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 3px;
  }
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 0, 0, 0.18);
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
      "content"
      "player";
  }

  .main-layout__card--sidebar {
    display: none;
  }
}
</style>
