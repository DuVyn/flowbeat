<script setup lang="ts">
/**
 * TrackGrid — 封面网格
 *
 * 适合展示发现页的图像化单曲卡片。
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
    emptyText: '暂无可展示的歌曲',
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
  <section class="track-grid">
    <div class="track-grid__header">
      <div>
        <p class="track-grid__eyebrow">{{ title }}</p>
        <h3 class="track-grid__title">{{ subtitle || title }}</h3>
      </div>
      <slot name="action" />
    </div>

    <div v-if="loading" class="track-grid__loading">
      <div v-for="i in 8" :key="i" class="track-grid__skeleton" />
    </div>

    <div v-else-if="tracks.length === 0" class="track-grid__empty">
      {{ emptyText }}
    </div>

    <div v-else class="track-grid__body">
      <button
        v-for="(track, index) in tracks"
        :key="track.id"
        type="button"
        class="track-grid__card"
        @click="handlePlay(track)"
      >
        <div class="track-grid__cover-wrap">
          <img
            class="track-grid__cover"
            :src="coverUrl(track)"
            :alt="`${track.name} 封面`"
            loading="lazy"
          />
          <span class="track-grid__index">#{{ index + 1 }}</span>
        </div>
        <div class="track-grid__meta">
          <p class="track-grid__name">{{ track.name }}</p>
          <p class="track-grid__artist">{{ track.artist }}</p>
          <span class="track-grid__duration">{{ formatDuration(track.durationMs) }}</span>
        </div>
      </button>
    </div>
  </section>
</template>

<style scoped>
.track-grid {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.track-grid__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
}

.track-grid__eyebrow {
  margin: 0 0 0.2rem;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(15, 23, 42, 0.42);
}

.track-grid__title {
  margin: 0;
  color: #163025;
  font-size: 1rem;
}

.track-grid__body {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.9rem;
}

.track-grid__card {
  padding: 0.7rem;
  border-radius: 20px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 14px 30px rgba(11, 30, 22, 0.06);
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.track-grid__card:hover {
  transform: translateY(-2px);
  border-color: rgba(34, 197, 94, 0.22);
  box-shadow: 0 18px 38px rgba(11, 30, 22, 0.12);
}

.track-grid__cover-wrap {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  aspect-ratio: 1 / 1;
  margin-bottom: 0.75rem;
}

.track-grid__cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.track-grid__index {
  position: absolute;
  left: 0.6rem;
  top: 0.6rem;
  padding: 0.28rem 0.5rem;
  border-radius: 999px;
  background: rgba(12, 18, 28, 0.72);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
}

.track-grid__meta {
  min-width: 0;
}

.track-grid__name {
  margin: 0 0 0.15rem;
  font-weight: 700;
  color: #163025;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-grid__artist {
  margin: 0;
  color: rgba(15, 23, 42, 0.48);
  font-size: 0.82rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.track-grid__duration {
  display: inline-block;
  margin-top: 0.25rem;
  color: rgba(15, 23, 42, 0.36);
  font-size: 0.76rem;
}

.track-grid__loading {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.9rem;
}

.track-grid__skeleton {
  aspect-ratio: 0.82 / 1;
  border-radius: 20px;
  background: linear-gradient(
    90deg,
    rgba(15, 23, 42, 0.06),
    rgba(15, 23, 42, 0.12),
    rgba(15, 23, 42, 0.06)
  );
  background-size: 200% 100%;
  animation: shimmer 1.3s infinite;
}

.track-grid__empty {
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
