<script setup lang="ts">
/**
 * HistoryPage — 用户历史播放页
 *
 * 保留触底分页加载与清空能力，使用统一虚拟列表展示历史记录。
 */

import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { clearPlayHistory, getLatestPlayHistory, getPlayHistory } from '@/api/history'
import { HttpError } from '@/api/http'
import MusicList from '@/components/music/MusicList.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import type { PlayHistoryItem, Track } from '@/types/music'

const PAGE_SIZE = 20
const CACHE_TTL_MS = 2 * 60 * 1000

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const playerStore = usePlayerStore()

const tracks = ref<PlayHistoryItem[]>([])
const latestTrack = ref<PlayHistoryItem | null>(null)
const loading = ref(true)
const loadingMore = ref(false)
const clearing = ref(false)
const loadError = ref('')
const hasMore = ref(false)

interface HistoryCache {
  tracks: PlayHistoryItem[]
  latestTrack: PlayHistoryItem | null
  hasMore: boolean
  timestamp: number
}

let pageCache: HistoryCache | null = null

const latestPlayedAtLabel = computed(() => {
  if (!latestTrack.value) {
    return ''
  }
  return formatDateTime(latestTrack.value.playedAt)
})

function formatDateTime(value: string): string {
  const datetime = new Date(value)
  if (Number.isNaN(datetime.getTime())) {
    return '-'
  }
  return datetime.toLocaleString('zh-CN', { hour12: false })
}

async function loadHistory(reset = false): Promise<void> {
  if (!reset && (!hasMore.value || loadingMore.value || loading.value)) {
    return
  }

  if (reset) {
    loading.value = true
    tracks.value = []
    hasMore.value = false
  } else {
    loadingMore.value = true
  }

  try {
    const offset = reset ? 0 : tracks.value.length
    const [historyResponse, latestResponse] = await Promise.all([
      getPlayHistory(PAGE_SIZE, offset),
      reset ? getLatestPlayHistory() : Promise.resolve(latestTrack.value),
    ])

    hasMore.value = historyResponse.hasMore
    tracks.value = reset ? historyResponse.items : [...tracks.value, ...historyResponse.items]
    latestTrack.value = latestResponse
    loadError.value = ''

    pageCache = {
      tracks: [...tracks.value],
      latestTrack: latestTrack.value,
      hasMore: hasMore.value,
      timestamp: Date.now(),
    }
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      authStore.clearSession()
      await router.replace({
        name: 'Login',
        query: { redirect: route.fullPath },
      })
      return
    }

    loadError.value = error instanceof Error ? error.message : '历史播放加载失败，请稍后重试'
    if (reset) {
      tracks.value = []
      hasMore.value = false
      latestTrack.value = null
    }
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function clearHistory(): Promise<void> {
  if (clearing.value) {
    return
  }

  const confirmed = window.confirm('确定要清空当前账号的历史播放记录吗？此操作无法撤销。')
  if (!confirmed) {
    return
  }

  clearing.value = true
  try {
    await clearPlayHistory()
    pageCache = null
    await loadHistory(true)
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '清空历史失败，请稍后重试'
  } finally {
    clearing.value = false
  }
}

function loadMoreHistory(): void {
  if (loading.value || loadingMore.value || loadError.value || !hasMore.value) {
    return
  }
  void loadHistory(false)
}

function handlePlay(track: Track): void {
  void playerStore.playTrack(track, tracks.value)
}

function handleResumeLatest(): void {
  if (!latestTrack.value) {
    return
  }
  void playerStore.playTrack(latestTrack.value, tracks.value)
}

onMounted(() => {
  if (pageCache && Date.now() - pageCache.timestamp < CACHE_TTL_MS) {
    tracks.value = pageCache.tracks
    latestTrack.value = pageCache.latestTrack
    hasMore.value = pageCache.hasMore
    loading.value = false
    return
  }

  void loadHistory(true)
})
</script>

<template>
  <div class="history-page">
    <header class="history-page__hero">
      <div>
        <h1 class="history-page__title">历史播放</h1>
        <p class="history-page__subtitle">按日期分组展示你听过的歌曲，清空后会重新回到空状态。</p>
      </div>

      <button
        class="history-page__clear"
        :disabled="loading || loadingMore || clearing"
        @click="clearHistory"
      >
        {{ clearing ? '清空中...' : '清空记录' }}
      </button>
    </header>

    <section class="history-page__summary-grid">
      <div class="history-page__summary-card history-page__summary-card--resume">
        <p class="history-page__summary-eyebrow">最近一次播放</p>
        <template v-if="latestTrack">
          <strong class="history-page__summary-title">{{ latestTrack.name }}</strong>
          <p class="history-page__summary-subtitle">{{ latestTrack.artist }}</p>
          <p v-if="latestPlayedAtLabel" class="history-page__summary-meta">
            {{ latestPlayedAtLabel }}
          </p>
          <button class="history-page__summary-button" @click="handleResumeLatest">继续播放</button>
        </template>
        <template v-else>
          <strong class="history-page__summary-title">暂无最近播放</strong>
          <p class="history-page__summary-subtitle">
            播放一首歌后，这里会自动记录最近一次听过的曲目。
          </p>
        </template>
      </div>

      <div class="history-page__summary-card history-page__summary-card--soft">
        <p class="history-page__summary-eyebrow">记录概览</p>
        <div class="history-page__summary-metrics">
          <div>
            <strong>{{ tracks.length }}</strong>
            <span>已加载记录</span>
          </div>
          <div>
            <strong>{{ hasMore ? '是' : '否' }}</strong>
            <span>还有更多</span>
          </div>
        </div>
        <p class="history-page__summary-note">
          {{ loadError || '虚拟列表会随着滚动只保留可视窗口，适合长历史记录回看。' }}
        </p>
      </div>
    </section>

    <div v-if="loadError" class="history-page__error">
      <span>{{ loadError }}</span>
      <button
        class="history-page__retry"
        :disabled="loading || loadingMore"
        @click="loadHistory(true)"
      >
        {{ loading ? '重试中...' : '重试' }}
      </button>
    </div>

    <section class="history-page__timeline">
      <MusicList
        title="历史播放列表"
        :tracks="tracks"
        :loading="loading"
        :has-more="hasMore"
        :loading-more="loadingMore"
        @play="handlePlay"
        @load-more="loadMoreHistory"
      />
      <div v-if="!loading && tracks.length === 0" class="history-page__empty">暂无历史播放记录</div>
    </section>
  </div>
</template>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  padding: 0.2rem 0 0.75rem;
  color: var(--ink-900);
}

.history-page__hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.history-page__summary-eyebrow {
  margin: 0 0 0.25rem;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-300);
}

.history-page__title {
  margin: 0;
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  letter-spacing: -0.04em;
  line-height: 1.08;
}

.history-page__subtitle,
.history-page__summary-subtitle,
.history-page__summary-note,
.history-page__summary-meta {
  margin: 0.45rem 0 0;
  color: var(--ink-500);
  font-size: 0.88rem;
  line-height: 1.5;
}

.history-page__clear,
.history-page__summary-button,
.history-page__retry {
  border: none;
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  background: var(--accent-600);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.16);
}

.history-page__clear:disabled,
.history-page__retry:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.history-page__summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.history-page__summary-card {
  padding: 0.85rem 0.95rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
}

.history-page__summary-title {
  display: block;
  font-size: 1rem;
}

.history-page__summary-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 0.35rem;
}

.history-page__summary-metrics div {
  padding: 0.65rem;
  border-radius: var(--radius-lg);
  background: var(--surface-1);
  border: 1px solid var(--surface-border);
}

.history-page__summary-metrics strong {
  display: block;
  font-size: 1.15rem;
  color: var(--accent-600);
}

.history-page__summary-metrics span {
  color: var(--ink-500);
  font-size: 0.76rem;
}

.history-page__summary-button {
  margin-top: 0.55rem;
}

.history-page__error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid rgba(220, 85, 85, 0.18);
  color: #9a2d2d;
  background: rgba(255, 235, 235, 0.72);
}

.history-page__timeline {
  padding: 0.9rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
}

.history-page__timeline-head {
  display: grid;
  grid-template-columns: 2rem 2fr 1.2fr 4rem;
  gap: 1rem;
  padding: 0 1rem;
  color: rgba(15, 23, 42, 0.42);
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.history-page__timeline-divider {
  height: 1px;
  margin: 0.5rem 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(15, 23, 42, 0.08) 15%,
    rgba(15, 23, 42, 0.08) 85%,
    transparent
  );
}

.history-page__group {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: 0.85rem;
}

.history-page__group-label {
  padding: 0 1rem 0.25rem;
  color: rgba(15, 23, 42, 0.58);
  font-size: 0.82rem;
  font-weight: 700;
}

.history-page__loading,
.history-page__empty,
.history-page__auto-loading,
.history-page__auto-load-tip {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 88px;
  color: rgba(15, 23, 42, 0.45);
}

.history-page__empty {
  min-height: 120px;
  border: 1px dashed rgba(15, 23, 42, 0.12);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.65);
}

@media (max-width: 960px) {
  .history-page__hero,
  .history-page__summary-grid,
  .history-page__error,
  .history-page__timeline-head {
    grid-template-columns: 1fr;
    display: grid;
  }

  .history-page__hero {
    display: grid;
  }

  .history-page__summary-grid {
    display: grid;
  }

  .history-page__timeline-head {
    display: grid;
  }
}
</style>
