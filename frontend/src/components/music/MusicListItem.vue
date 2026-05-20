<script setup lang="ts">
/**
 * MusicListItem — 音乐列表单行组件
 *
 * 负责渲染一首歌曲的完整信息行：序号、封面、歌名、艺术家、时长。
 * 悬停时显示播放按钮覆盖层，提供视觉交互反馈。
 *
 * Props:
 *   - track: Track 对象
 *   - index: 在列表中的序号（从 1 开始）
 */

import { computed } from 'vue'
import type { Track } from '@/types/music'
import mockCover from '@/assets/images/default-cover.svg'
import { formatDuration } from '@/utils/TimeFormat'
import { useCoverStore } from '@/stores/cover'

const props = withDefaults(
  defineProps<{
    /** 歌曲数据 */
    track: Track
    /** 列表序号（1-based） */
    index: number
    /** 是否显示行内收藏按钮 */
    showLikeAction?: boolean
  }>(),
  {
    showLikeAction: false,
  },
)

const emit = defineEmits<{
  /** 点击播放/选中该曲目 */
  (e: 'play', track: Track): void
  /** 点击收藏动作 */
  (e: 'toggle-like', track: Track): void
}>()

const coverStore = useCoverStore()

const coverUrl = computed(() => {
  const cached = coverStore.getCoverUrl(props.track.id)
  if (cached) return cached
  const raw = props.track.coverUrl?.trim()
  if (raw) return raw
  return mockCover
})

function handlePlay() {
  emit('play', props.track)
}

function handleToggleLike(event: MouseEvent) {
  event.stopPropagation()
  emit('toggle-like', props.track)
}
</script>

<template>
  <div
    class="music-list-item"
    :class="{ 'music-list-item--with-action': showLikeAction }"
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
          :src="coverUrl"
          :alt="`${track.name} 封面`"
          loading="lazy"
          width="44"
          height="44"
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

    <!-- 时长 -->
    <span class="music-list-item__duration">{{ formatDuration(track.durationMs) }}</span>

    <button
      v-if="showLikeAction"
      type="button"
      class="music-list-item__favorite-btn"
      :class="{ 'music-list-item__favorite-btn--liked': track.isLiked }"
      :aria-label="track.isLiked ? '取消收藏' : '收藏歌曲'"
      @click="handleToggleLike"
    >
      <svg
        viewBox="0 0 24 24"
        :fill="track.isLiked ? 'currentColor' : 'none'"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
        />
      </svg>
    </button>
  </div>
</template>

<style scoped>
/* ========================================
 * 单行容器
 * ======================================== */
.music-list-item {
  display: grid;
  grid-template-columns: 2rem 1fr 4.5rem;
  align-items: center;
  gap: 1rem;
  padding: 0.25rem 1rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    transform 0.15s ease;
  user-select: none;
}

.music-list-item--with-action {
  grid-template-columns: 2rem 1fr 4.5rem auto;
}

.music-list-item:hover {
  background-color: rgba(15, 23, 42, 0.04);
}

.music-list-item:active {
  transform: scale(0.995);
}

/* ---- 序号 ---- */
.music-list-item__index {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--ink-300);
  text-align: center;
  font-variant-numeric: tabular-nums;
}

/* ---- 封面 + 歌曲信息组 ---- */
.music-list-item__info {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
}

/* ---- 封面包装（含播放覆盖） ---- */
.music-list-item__cover-wrapper {
  position: relative;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 10px;
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
  color: var(--ink-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.music-list-item__artist {
  font-size: 0.78rem;
  color: var(--ink-300);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- 时长 ---- */
.music-list-item__duration {
  font-size: 0.85rem;
  color: var(--ink-300);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.music-list-item__favorite-btn {
  border: none;
  background: transparent;
  color: rgba(225, 85, 97, 0.5);
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition:
    color 0.2s ease,
    background-color 0.2s ease,
    transform 0.15s ease;
}

.music-list-item__favorite-btn svg {
  width: 18px;
  height: 18px;
}

.music-list-item__favorite-btn:hover {
  background: rgba(225, 85, 97, 0.08);
  color: rgba(225, 85, 97, 0.9);
}

.music-list-item__favorite-btn--liked {
  color: #e15561;
}

.music-list-item__favorite-btn:active {
  transform: scale(0.96);
}

/* ========================================
 * 响应式：移动端
 * ======================================== */
@media (max-width: 640px) {
  .music-list-item {
    grid-template-columns: 1.5rem 1fr 3.5rem;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
  }

  .music-list-item--with-action {
    grid-template-columns: 1.5rem 1fr 3.5rem auto;
  }
}
</style>
