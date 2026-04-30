<script setup lang="ts">
/**
 * MusicList — 虚拟滚动音乐列表
 *
 * 使用固定行高虚拟化，避免无限追加导致 DOM 膨胀。
 * 同时内置触底分页信号，承接后端 limit/offset 分页接口。
 */

import { computed, nextTick, ref, shallowRef, watch } from 'vue'
import type { Track } from '@/types/music'
import MusicListItem from './MusicListItem.vue'
import { useCoverStore } from '@/stores/cover'

const props = withDefaults(
  defineProps<{
    tracks: Track[]
    title?: string
    loading?: boolean
    hasMore?: boolean
    loadingMore?: boolean
    rowHeight?: number
    viewportHeight?: number
    overscan?: number
    showLikeAction?: boolean
  }>(),
  {
    title: '',
    loading: false,
    hasMore: false,
    loadingMore: false,
    rowHeight: 64,
    viewportHeight: 520,
    overscan: 6,
    showLikeAction: false,
  },
)

const emit = defineEmits<{
  (e: 'play', track: Track): void
  (e: 'load-more'): void
  (e: 'toggle-like', track: Track): void
}>()

const coverStore = useCoverStore()
const viewportEl = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const frozenTracks = shallowRef<readonly Track[]>(Object.freeze([]) as readonly Track[])

const totalCount = computed(() => frozenTracks.value.length)
const totalHeight = computed(() => totalCount.value * props.rowHeight)
const visibleCount = computed(
  () => Math.ceil(props.viewportHeight / props.rowHeight) + props.overscan * 2,
)
const startIndex = computed(() =>
  Math.max(0, Math.floor(scrollTop.value / props.rowHeight) - props.overscan),
)
const endIndex = computed(() => Math.min(totalCount.value, startIndex.value + visibleCount.value))
const topPadding = computed(() => startIndex.value * props.rowHeight)
const visibleTracks = computed(() => frozenTracks.value.slice(startIndex.value, endIndex.value))

function handlePlay(track: Track): void {
  emit('play', track)
}

function handleToggleLike(track: Track): void {
  emit('toggle-like', track)
}

function tryEmitLoadMore(container: HTMLElement | null = viewportEl.value): void {
  if (!container || props.loading || props.loadingMore || !props.hasMore) {
    return
  }
  const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight
  if (distanceToBottom <= props.rowHeight * 2) {
    emit('load-more')
  }
}

function handleViewportScroll(event: Event): void {
  const target = event.target
  if (!(target instanceof HTMLElement)) {
    return
  }
  scrollTop.value = target.scrollTop
  tryEmitLoadMore(target)
}

watch(
  () => props.tracks,
  (newTracks) => {
    const immutableTracks = Object.freeze([...newTracks]) as readonly Track[]
    frozenTracks.value = immutableTracks

    if (newTracks.length > 0) {
      void coverStore.resolveCovers(newTracks.map((track) => track.id))
    }

    void nextTick().then(() => {
      tryEmitLoadMore()
    })
  },
  { immediate: true, deep: true },
)

watch(
  () => [props.hasMore, props.loading, props.loadingMore],
  () => {
    void nextTick().then(() => {
      tryEmitLoadMore()
    })
  },
)
</script>

<template>
  <section class="music-list" aria-label="歌曲列表">
    <h2 v-if="title" class="music-list__title">{{ title }}</h2>

    <div
      class="music-list__header"
      :class="{ 'music-list__header--with-action': showLikeAction }"
      role="row"
      aria-hidden="true"
    >
      <span class="music-list__header-index">#</span>
      <span class="music-list__header-info">歌名 / 歌手</span>
      <span class="music-list__header-duration">
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
      <span v-if="showLikeAction" class="music-list__header-action"></span>
    </div>

    <div class="music-list__divider" />

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
        <div class="skeleton-line skeleton-line--duration" />
      </div>
    </div>

    <div v-else-if="totalCount === 0" class="music-list__empty">
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

    <div
      v-else
      ref="viewportEl"
      class="music-list__viewport"
      role="rowgroup"
      :style="{ maxHeight: `${viewportHeight}px` }"
      @scroll.passive="handleViewportScroll"
    >
      <div class="music-list__virtual-space" :style="{ height: `${totalHeight}px` }">
        <div
          class="music-list__virtual-window"
          :style="{ transform: `translateY(${topPadding}px)` }"
        >
          <MusicListItem
            v-for="(track, idx) in visibleTracks"
            :key="track.id"
            :track="track"
            :index="startIndex + idx + 1"
            :show-like-action="showLikeAction"
            @play="handlePlay"
            @toggle-like="handleToggleLike"
          />
        </div>
      </div>
    </div>

    <div v-if="!loading && totalCount > 0" class="music-list__footer">
      <span>共 {{ totalCount }} 首歌曲</span>
      <span v-if="loadingMore" class="music-list__footer-status">正在加载更多...</span>
      <span v-else-if="hasMore" class="music-list__footer-status">继续下滑可自动加载更多</span>
    </div>
  </section>
</template>

<style scoped>
.music-list {
  width: 100%;
}

.music-list__title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1a2e1a;
  margin: 0 0 1.25rem;
  letter-spacing: -0.01em;
}

.music-list__header {
  display: grid;
  grid-template-columns: 2rem 1fr 4rem;
  align-items: center;
  gap: 1rem;
  padding: 0 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.38);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.music-list__header--with-action {
  grid-template-columns: 2rem 1fr 4rem auto;
}

.music-list__header-action {
  width: 2rem;
  justify-self: end;
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

.music-list__viewport {
  overflow-y: auto;
  overscroll-behavior: contain;
}

.music-list__virtual-space {
  position: relative;
  width: 100%;
}

.music-list__virtual-window {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  will-change: transform;
}

.music-list__footer {
  margin-top: 0.9rem;
  padding: 0 1rem;
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.36);
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.music-list__footer-status {
  color: rgba(15, 23, 42, 0.48);
}

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

.music-list__skeleton {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.music-list__skeleton-row {
  display: grid;
  grid-template-columns: 2rem 44px 1fr 4rem;
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

@media (max-width: 640px) {
  .music-list__header {
    grid-template-columns: 1.5rem 1fr 3.5rem;
  }

  .music-list__skeleton-row {
    grid-template-columns: 1.5rem 40px 1fr 3.5rem;
  }

  .music-list__footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }
}
</style>
