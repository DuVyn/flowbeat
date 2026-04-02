<script setup lang="ts">
/**
 * MusicList — 音乐列表容器组件
 *
 * 负责组织和展示歌曲数据集合，包含：
 *   - 列表标题（可选）
 *   - 表头行（歌名/歌手 · 专辑 · 时长）
 *   - 循环渲染 MusicListItem
 *   - loading 骨架屏状态
 *   - empty 空数据提示状态
 *
 * Props:
 *   - tracks: 歌曲数组
 *   - title: 列表标题（可选）
 *   - loading: 是否加载中
 */

import type { Track } from '@/types/music'
import MusicListItem from './MusicListItem.vue'

withDefaults(
  defineProps<{
    /** 歌曲数据列表 */
    tracks: Track[]
    /** 列表标题 */
    title?: string
    /** 是否处于加载状态 */
    loading?: boolean
  }>(),
  {
    title: '',
    loading: false,
  },
)

const emit = defineEmits<{
  /** 点击播放某首歌 */
  (e: 'play', track: Track): void
}>()

function handlePlay(track: Track) {
  emit('play', track)
}
</script>

<template>
  <section class="music-list" aria-label="歌曲列表">
    <!-- 列表标题 -->
    <h2 v-if="title" class="music-list__title">{{ title }}</h2>

    <!-- 表头 -->
    <div class="music-list__header" role="row" aria-hidden="true">
      <span class="music-list__header-index">#</span>
      <span class="music-list__header-info">歌名 / 歌手</span>
      <span class="music-list__header-album">专辑</span>
      <span class="music-list__header-duration">
        <!-- 时钟图标 -->
        <svg
          class="music-list__clock-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      </span>
    </div>

    <!-- 分隔线 -->
    <div class="music-list__divider" />

    <!-- Loading 骨架屏 -->
    <div v-if="loading" class="music-list__skeleton">
      <div
        v-for="i in 6"
        :key="i"
        class="music-list__skeleton-row"
        :style="{ animationDelay: `${i * 80}ms` }"
      >
        <div class="skeleton-index" />
        <div class="skeleton-cover" />
        <div class="skeleton-text">
          <div class="skeleton-line skeleton-line--name" />
          <div class="skeleton-line skeleton-line--artist" />
        </div>
        <div class="skeleton-line skeleton-line--album" />
        <div class="skeleton-line skeleton-line--duration" />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="tracks.length === 0" class="music-list__empty">
      <svg
        class="music-list__empty-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M9 18V5l12-2v13" />
        <circle cx="6" cy="18" r="3" />
        <circle cx="18" cy="16" r="3" />
      </svg>
      <p class="music-list__empty-text">暂无歌曲</p>
      <p class="music-list__empty-hint">试试搜索或浏览推荐内容</p>
    </div>

    <!-- 歌曲列表 -->
    <TransitionGroup
      v-else
      name="list"
      tag="div"
      class="music-list__body"
      role="rowgroup"
    >
      <MusicListItem
        v-for="(track, idx) in tracks"
        :key="track.id"
        :track="track"
        :index="idx + 1"
        @play="handlePlay"
      />
    </TransitionGroup>

    <!-- 列表底部统计 -->
    <div v-if="!loading && tracks.length > 0" class="music-list__footer">
      共 {{ tracks.length }} 首歌曲
    </div>
  </section>
</template>

<style scoped>
/* ========================================
 * 列表容器
 * ======================================== */
.music-list {
  width: 100%;
}

/* ---- 标题 ---- */
.music-list__title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1a2e1a;
  margin: 0 0 1.25rem;
  letter-spacing: -0.01em;
}

/* ========================================
 * 表头
 * ======================================== */
.music-list__header {
  display: grid;
  grid-template-columns: 2rem 2fr 1.2fr 4rem;
  align-items: center;
  gap: 1rem;
  padding: 0 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.38);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.music-list__header-index {
  text-align: center;
}

.music-list__header-duration {
  text-align: right;
  display: flex;
  justify-content: flex-end;
}

.music-list__clock-icon {
  width: 14px;
  height: 14px;
}

/* ---- 分隔线 ---- */
.music-list__divider {
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(0, 0, 0, 0.08) 15%,
    rgba(0, 0, 0, 0.08) 85%,
    transparent
  );
  margin: 0.5rem 0;
}

/* ========================================
 * 列表体
 * ======================================== */
.music-list__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* ========================================
 * TransitionGroup 动画
 * ======================================== */
.list-enter-active {
  transition: all 0.35s ease;
}

.list-leave-active {
  transition: all 0.25s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* ========================================
 * 底部统计
 * ======================================== */
.music-list__footer {
  margin-top: 1rem;
  padding: 0 1rem;
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.32);
}

/* ========================================
 * 空状态
 * ======================================== */
.music-list__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
}

.music-list__empty-icon {
  width: 56px;
  height: 56px;
  color: rgba(76, 175, 80, 0.3);
  margin-bottom: 1rem;
}

.music-list__empty-text {
  font-size: 1rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.45);
  margin: 0 0 0.25rem;
}

.music-list__empty-hint {
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.3);
  margin: 0;
}

/* ========================================
 * Loading 骨架屏
 * ======================================== */
.music-list__skeleton {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.music-list__skeleton-row {
  display: grid;
  grid-template-columns: 2rem 44px 1fr 1.2fr 4rem;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  animation: skeleton-fade-in 0.4s ease both;
}

@keyframes skeleton-fade-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 骨架屏元素 */
.skeleton-index,
.skeleton-cover,
.skeleton-line {
  background: linear-gradient(
    90deg,
    rgba(0, 0, 0, 0.05) 25%,
    rgba(0, 0, 0, 0.09) 50%,
    rgba(0, 0, 0, 0.05) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.6s ease-in-out infinite;
  border-radius: 4px;
}

.skeleton-index {
  width: 16px;
  height: 14px;
  margin: 0 auto;
}

.skeleton-cover {
  width: 44px;
  height: 44px;
  border-radius: 6px;
}

.skeleton-text {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-line--name {
  width: 55%;
  height: 12px;
}

.skeleton-line--artist {
  width: 35%;
  height: 10px;
}

.skeleton-line--album {
  width: 45%;
  height: 12px;
}

.skeleton-line--duration {
  width: 32px;
  height: 12px;
  margin-left: auto;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* ========================================
 * 响应式
 * ======================================== */
@media (max-width: 640px) {
  .music-list__header {
    grid-template-columns: 1.5rem 1fr 3.5rem;
  }

  .music-list__header-album {
    display: none;
  }

  .music-list__skeleton-row {
    grid-template-columns: 1.5rem 40px 1fr 3.5rem;
  }
}
</style>
