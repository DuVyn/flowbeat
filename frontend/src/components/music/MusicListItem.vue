<script setup lang="ts">
/**
 * MusicListItem — 音乐列表单行组件
 *
 * 负责渲染一首歌曲的完整信息行：序号、封面、歌名、艺术家、专辑名、时长。
 * 悬停时显示播放按钮覆盖层，提供视觉交互反馈。
 *
 * Props:
 *   - track: Track 对象
 *   - index: 在列表中的序号（从 1 开始）
 */

import type { Track } from '@/types/music'
import mockCover from '@/assets/images/mock-cover-sunny.png'
import { formatDuration } from '@/utils/TimeFormat'

const props = defineProps<{
  /** 歌曲数据 */
  track: Track
  /** 列表序号（1-based） */
  index: number
}>()

const emit = defineEmits<{
  /** 点击播放/选中该曲目 */
  (e: 'play', track: Track): void
}>()

function handlePlay() {
  emit('play', props.track)
}

function resolveCoverUrl(rawUrl: string): string {
  return rawUrl.trim() ? rawUrl : mockCover
}
</script>

<template>
  <div
    class="music-list-item"
    role="row"
    :aria-label="`${track.name} - ${track.artist}`"
    @click="handlePlay"
  >
    <!-- 序号 -->
    <span class="music-list-item__index">{{ index }}</span>

    <!-- 封面 + 歌曲信息 -->
    <div class="music-list-item__info">
      <div class="music-list-item__cover-wrapper">
        <img
          class="music-list-item__cover"
          :src="resolveCoverUrl(track.coverUrl)"
          :alt="`${track.album} 封面`"
          loading="lazy"
        />
        <!-- 悬停播放按钮 -->
        <div class="music-list-item__play-overlay">
          <svg class="music-list-item__play-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
      <div class="music-list-item__text">
        <span class="music-list-item__name">{{ track.name }}</span>
        <span class="music-list-item__artist">{{ track.artist }}</span>
      </div>
    </div>

    <!-- 专辑名 -->
    <span class="music-list-item__album">{{ track.album }}</span>

    <!-- 时长 -->
    <span class="music-list-item__duration">{{ formatDuration(track.durationMs) }}</span>
  </div>
</template>

<style scoped>
/* ========================================
 * 单行容器
 * ======================================== */
.music-list-item {
  display: grid;
  grid-template-columns: 2rem 2fr 1.2fr 4rem;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    transform 0.15s ease;
  user-select: none;
}

.music-list-item:hover {
  background-color: rgba(76, 175, 80, 0.06);
}

.music-list-item:active {
  transform: scale(0.995);
}

/* ---- 序号 ---- */
.music-list-item__index {
  font-size: 0.85rem;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.36);
  text-align: center;
  font-variant-numeric: tabular-nums;
}

/* ---- 封面 + 歌曲信息组 ---- */
.music-list-item__info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

/* ---- 封面包装（含播放覆盖） ---- */
.music-list-item__cover-wrapper {
  position: relative;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
}

.music-list-item__cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: filter 0.25s ease;
}

.music-list-item__play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.music-list-item:hover .music-list-item__play-overlay {
  opacity: 1;
}

.music-list-item:hover .music-list-item__cover {
  filter: brightness(0.85);
}

.music-list-item__play-icon {
  width: 20px;
  height: 20px;
  color: #fff;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

/* ---- 歌名与艺术家 ---- */
.music-list-item__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.music-list-item__name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1a2e1a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-list-item__artist {
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.45);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- 专辑名 ---- */
.music-list-item__album {
  font-size: 0.85rem;
  color: rgba(0, 0, 0, 0.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- 时长 ---- */
.music-list-item__duration {
  font-size: 0.85rem;
  color: rgba(0, 0, 0, 0.42);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* ========================================
 * 响应式：移动端
 * ======================================== */
@media (max-width: 640px) {
  .music-list-item {
    grid-template-columns: 1.5rem 1fr 3.5rem;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
  }

  /* 隐藏专辑列 */
  .music-list-item__album {
    display: none;
  }
}
</style>
