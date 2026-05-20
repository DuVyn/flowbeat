<script setup lang="ts">
/**
 * TrackRail — 横向歌曲轨道
 *
 * 适合展示最近播放、精选推荐等横向卡片流。
 */

import { watch } from 'vue'

import mockCover from '@/assets/images/default-cover.svg'
import { useCoverStore } from '@/stores/cover'
import type { Track } from '@/types/music'
import { formatDuration } from '@/utils/TimeFormat'

const props = withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    tracks: Track[]
    loading?: boolean
    emptyText?: string
    layout?: 'scroll' | 'grid'
    columns?: number
  }>(),
  {
    subtitle: '',
    loading: false,
    emptyText: '暂无歌曲可展示',
    layout: 'scroll',
    columns: 8,
  },
)

const emit = defineEmits<{
  (e: 'play', track: Track): void
}>()

const coverStore = useCoverStore()

watch(
  () => props.tracks,
  (newTracks) => {
    if (newTracks && newTracks.length > 0) {
      void coverStore.resolveCovers(newTracks.map((t) => t.id))
    }
  },
  { immediate: true, deep: true },
)

function coverUrl(track: Track): string {
  const cached = coverStore.getCoverUrl(track.id)
  if (cached) {
    return cached
  }
  return track.coverUrl?.trim() || mockCover
}

function handlePlay(track: Track): void {
  emit('play', track)
}
</script>

<template>
  <section class="track-rail">
    <div class="track-rail__header">
      <div>
        <p class="track-rail__eyebrow">{{ title }}</p>
        <h3 class="track-rail__title">{{ subtitle || title }}</h3>
      </div>
      <slot name="action" />
    </div>

    <div
      v-if="loading"
      class="track-rail__loading"
      :class="{ 'track-rail__loading--grid': layout === 'grid' }"
    >
      <div v-for="i in 5" :key="i" class="track-rail__skeleton" />
    </div>

    <div v-else-if="tracks.length === 0" class="track-rail__empty">
      {{ emptyText }}
    </div>

    <div
      v-else
      class="track-rail__scroller"
      :class="{ 'track-rail__scroller--grid': layout === 'grid' }"
      :style="layout === 'grid' ? { '--track-rail-columns': String(columns) } : undefined"
    >
      <button
        v-for="track in tracks"
        :key="track.id"
        type="button"
        class="track-rail__card"
        @click="handlePlay(track)"
      >
        <img
          class="track-rail__cover"
          :src="coverUrl(track)"
          :alt="`${track.name} 封面`"
          loading="lazy"
        />
        <div class="track-rail__meta">
          <p class="track-rail__name">{{ track.name }}</p>
          <p class="track-rail__artist">{{ track.artist }}</p>
          <span class="track-rail__duration">{{ formatDuration(track.durationMs) }}</span>
        </div>
      </button>
    </div>
  </section>
</template>

<style scoped>
.track-rail {
  --track-rail-columns: 8;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}

.track-rail__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
}

.track-rail__eyebrow {
  margin: 0 0 0.5rem;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--ink-300);
}

.track-rail__title {
  margin: 0;
  color: var(--ink-900);
  font-size: 1rem;
}

.track-rail__scroller {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(200px, 1fr);
  gap: 0.5rem;
  overflow-x: auto;
  width: 100%;
  min-width: 0;
  padding-bottom: 0.35rem;
  scroll-snap-type: x proximity;
}

.track-rail__scroller--grid {
  grid-auto-flow: row;
  grid-auto-columns: initial;
  grid-template-columns: repeat(var(--track-rail-columns), minmax(0, 1fr));
  overflow-x: hidden;
  padding-bottom: 0;
  scroll-snap-type: none;
}

.track-rail__card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
  scroll-snap-align: start;
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.track-rail__scroller--grid .track-rail__card {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4rem;
}

.track-rail__card:hover {
  transform: translateY(-2px);
  border-color: rgba(20, 91, 67, 0.3);
  box-shadow: var(--shadow-strong);
}

.track-rail__cover {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  object-fit: cover;
  flex-shrink: 0;
}

.track-rail__scroller--grid .track-rail__cover {
  width: 100%;
  height: auto;
  aspect-ratio: 1 / 1;
  border-radius: 14px;
}

.track-rail__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.track-rail__scroller--grid .track-rail__meta {
  width: 100%;
}

.track-rail__name {
  margin: 0;
  font-weight: 700;
  color: var(--ink-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-rail__artist {
  margin: 0;
  color: var(--ink-500);
  font-size: 0.82rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-rail__duration {
  font-size: 0.76rem;
  color: var(--ink-300);
}

@media (max-width: 1280px) {
  .track-rail__scroller--grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .track-rail__loading--grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .track-rail__scroller--grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .track-rail__loading--grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.track-rail__loading {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(200px, 1fr);
  gap: 0.5rem;
}

.track-rail__loading--grid {
  grid-auto-flow: row;
  grid-auto-columns: initial;
  grid-template-columns: repeat(var(--track-rail-columns), minmax(0, 1fr));
}

.track-rail__skeleton {
  min-height: 96px;
  border-radius: var(--radius-lg);
  background: linear-gradient(
    90deg,
    rgba(15, 23, 42, 0.06),
    rgba(15, 23, 42, 0.12),
    rgba(15, 23, 42, 0.06)
  );
  background-size: 200% 100%;
  animation: shimmer 1.3s infinite;
}

.track-rail__empty {
  padding: 1rem;
  border-radius: var(--radius-lg);
  border: 1px dashed var(--surface-border);
  color: var(--ink-500);
  background: var(--surface-1);
}

@keyframes shimmer {
  0% {
    background-position: 0 0;
  }

  100% {
    background-position: 200% 0;
  }
}
</style>
