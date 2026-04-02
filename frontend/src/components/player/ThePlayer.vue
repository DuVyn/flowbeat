<script setup lang="ts">
/**
 * ThePlayer — 底部常驻播放器
 *
 * 单行水平布局：
 *   [封面][歌名/歌手][♥]  [⏮][⏯][⏭] [---进度条---] [时间]  [🔊][音量]
 *
 * 当前使用 Mock 数据，后续接入 usePlayer composable。
 */

import { ref, computed } from 'vue'

/* ---- Mock 歌曲数据 ---- */
const currentSong = ref({
  title: '晴天',
  artist: '周杰伦',
  cover: '',
  duration: 269,
})

/* ---- 播放状态 ---- */
const isPlaying = ref(false)
const currentTime = ref(0)
const volume = ref(80)
const isMuted = ref(false)
const isLiked = ref(false)

/* ---- 计算属性 ---- */
const progressPercent = computed(() => {
  if (!currentSong.value.duration) return 0
  return (currentTime.value / currentSong.value.duration) * 100
})
const effectiveVolume = computed(() => (isMuted.value ? 0 : volume.value))

/* ---- 时间格式化 ---- */
function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

/* ---- 控制方法 ---- */
function togglePlay() {
  isPlaying.value = !isPlaying.value
}
function prevTrack() {
  currentTime.value = 0
}
function nextTrack() {
  currentTime.value = 0
}
function toggleLike() {
  isLiked.value = !isLiked.value
}
function toggleMute() {
  isMuted.value = !isMuted.value
}
function onProgressInput(e: Event) {
  const val = Number((e.target as HTMLInputElement).value)
  currentTime.value = (val / 100) * currentSong.value.duration
}
function onVolumeInput(e: Event) {
  volume.value = Number((e.target as HTMLInputElement).value)
  if (volume.value > 0) isMuted.value = false
}
</script>

<template>
  <div class="player">
    <!-- ===== 左：歌曲信息 ===== -->
    <div class="player__info">
      <div class="player__cover">
        <svg v-if="!currentSong.cover" viewBox="0 0 24 24" fill="currentColor" class="player__cover-icon">
          <path d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM21 16c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z"/>
        </svg>
        <img v-else :src="currentSong.cover" :alt="currentSong.title" />
      </div>
      <div class="player__meta">
        <span class="player__title">{{ currentSong.title }}</span>
        <span class="player__artist">{{ currentSong.artist }}</span>
      </div>
      <button
        class="player__icon-btn"
        :class="{ 'player__icon-btn--liked': isLiked }"
        @click="toggleLike"
      >
        <svg viewBox="0 0 24 24" :fill="isLiked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
          <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
        </svg>
      </button>
    </div>

    <!-- ===== 中：控制按钮 + 进度条（水平） ===== -->
    <div class="player__center">
      <!-- 按钮组 -->
      <div class="player__buttons">
        <button class="player__icon-btn" @click="prevTrack" aria-label="上一首">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
        </button>
        <button class="player__play-btn" @click="togglePlay" :aria-label="isPlaying ? '暂停' : '播放'">
          <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        </button>
        <button class="player__icon-btn" @click="nextTrack" aria-label="下一首">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
        </button>
      </div>

      <!-- 进度条（与按钮水平） -->
      <span class="player__time">{{ formatTime(currentTime) }}</span>
      <div class="player__progress">
        <input
          type="range" min="0" max="100" step="0.1"
          :value="progressPercent"
          class="player__range player__range--progress"
          :style="{ '--pct': progressPercent + '%' }"
          @input="onProgressInput"
          aria-label="播放进度"
        />
      </div>
      <span class="player__time">{{ formatTime(currentSong.duration) }}</span>
    </div>

    <!-- ===== 右：音量 ===== -->
    <div class="player__right">
      <button class="player__icon-btn" @click="toggleMute">
        <svg v-if="isMuted || volume === 0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>
        </svg>
        <svg v-else-if="volume < 50" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
        </svg>
      </button>
      <div class="player__vol-bar">
        <input
          type="range" min="0" max="100" step="1"
          :value="effectiveVolume"
          class="player__range player__range--vol"
          :style="{ '--pct': effectiveVolume + '%' }"
          @input="onVolumeInput"
          aria-label="音量"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ========================================
 * 播放器 — 单行三段式水平布局
 * ======================================== */
.player {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 1rem;
  gap: 1rem;
}

/* ===== 左段：歌曲信息 ===== */
.player__info {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  min-width: 180px;
  flex-shrink: 0;
}

.player__cover {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: rgba(76, 175, 125, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}
.player__cover img { width: 100%; height: 100%; object-fit: cover; }
.player__cover-icon { width: 22px; height: 22px; color: rgba(76, 175, 125, 0.45); }

.player__meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.player__title {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #1a2e1a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.player__artist {
  font-size: 0.6875rem;
  color: rgba(0, 0, 0, 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 中段：按钮 + 进度条（水平一行） ===== */
.player__center {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.player__buttons {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

/* 播放/暂停大按钮 */
.player__play-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: #1a2e1a;
  color: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;
}
.player__play-btn:hover {
  transform: scale(1.06);
  box-shadow: 0 0 16px rgba(0, 0, 0, 0.12);
}
.player__play-btn:active { transform: scale(0.96); }
.player__play-btn svg { width: 16px; height: 16px; }

.player__time {
  font-size: 0.6875rem;
  color: rgba(0, 0, 0, 0.35);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
  min-width: 2rem;
  text-align: center;
}

.player__progress {
  flex: 1;
  min-width: 0;
}

/* ===== 右段：音量 ===== */
.player__right {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}
.player__vol-bar {
  width: 90px;
}

/* ===== 通用小图标按钮 ===== */
.player__icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: rgba(0, 0, 0, 0.4);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.player__icon-btn:hover { color: #1a2e1a; }
.player__icon-btn svg { width: 16px; height: 16px; }
.player__icon-btn--liked { color: #e85d75; }
.player__icon-btn--liked:hover { color: #d1465e; }

/* ===== 通用 range 滑条 ===== */
.player__range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  outline: none;
  cursor: pointer;
  background: linear-gradient(
    to right,
    rgba(0, 0, 0, 0.35) 0%,
    rgba(0, 0, 0, 0.35) var(--pct, 0%),
    rgba(0, 0, 0, 0.08) var(--pct, 0%),
    rgba(0, 0, 0, 0.08) 100%
  );
  transition: height 0.12s ease;
}
.player__range:hover { height: 5px; }

.player__range--progress {
  background: linear-gradient(
    to right,
    #4caf7d 0%,
    #6bcf9a var(--pct, 0%),
    rgba(0, 0, 0, 0.08) var(--pct, 0%),
    rgba(0, 0, 0, 0.08) 100%
  );
}

/* 滑块（默认隐藏, hover 显示） */
.player__range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: #1a2e1a;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
  opacity: 0;
  transition: opacity 0.12s ease;
}
.player__range:hover::-webkit-slider-thumb { opacity: 1; }

.player__range::-moz-range-thumb {
  width: 12px; height: 12px;
  border: none; border-radius: 50%;
  background: #1a2e1a;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
  opacity: 0;
  transition: opacity 0.12s ease;
}
.player__range:hover::-moz-range-thumb { opacity: 1; }
</style>
