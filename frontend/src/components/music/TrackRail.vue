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
  }>(),
  {
    subtitle: '',
    loading: false,
    emptyText: '暂无歌曲可展示',
  },
)

const emit = defineEmits<{
  (e: 'play', track: Track): void
}>()

const coverStore = useCoverStore()

watch(
  () => props.tracks,
  (newTracks, oldTracks) => {
    const oldIds = new Set((oldTracks ?? []).map((track) => track.id))
    const appendedIds = newTracks.map((track) => track.id).filter((id) => !oldIds.has(id))
    if (appendedIds.length > 0) {
      void coverStore.resolveCovers(appendedIds)
    }
  },
  { immediate: true },
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

    <div v-if="loading" class="track-rail__loading">
      <div v-for="i in 5" :key="i" class="track-rail__skeleton" />
    </div>

    <div v-else-if="tracks.length === 0" class="track-rail__empty">
      {{ emptyText }}
    </div>

    <div v-else class="track-rail__scroller">
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
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.track-rail__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
}

.track-rail__eyebrow {
  margin: 0 0 0.2rem;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(15, 23, 42, 0.42);
}

.track-rail__title {
  margin: 0;
  color: #163025;
  font-size: 1rem;
}

.track-rail__scroller {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(180px, 1fr);
  gap: 0.9rem;
  overflow-x: auto;
  padding-bottom: 0.35rem;
  scroll-snap-type: x proximity;
}

.track-rail__card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.8rem;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 14px 34px rgba(11, 30, 22, 0.06);
  scroll-snap-align: start;
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.track-rail__card:hover {
  transform: translateY(-2px);
  border-color: rgba(34, 197, 94, 0.22);
  box-shadow: 0 18px 40px rgba(11, 30, 22, 0.12);
}

.track-rail__cover {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  object-fit: cover;
  flex-shrink: 0;
}

.track-rail__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.track-rail__name {
  margin: 0;
  font-weight: 700;
  color: #163025;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-rail__artist {
  margin: 0;
  color: rgba(15, 23, 42, 0.48);
  font-size: 0.82rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-rail__duration {
  font-size: 0.76rem;
  color: rgba(15, 23, 42, 0.38);
}

.track-rail__loading {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(180px, 1fr);
  gap: 0.9rem;
}

.track-rail__skeleton {
  min-height: 96px;
  border-radius: 18px;
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
  border-radius: 18px;
  border: 1px dashed rgba(15, 23, 42, 0.12);
  color: rgba(15, 23, 42, 0.45);
  background: rgba(255, 255, 255, 0.62);
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
