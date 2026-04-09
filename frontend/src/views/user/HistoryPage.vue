<script setup lang="ts">
/**
 * HistoryPage — 用户历史播放页
 *
 * 展示当前用户最近播放历史，支持滚动触底自动加载与点击回放。
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getPlayHistory } from '@/api/history'
import { HttpError } from '@/api/http'
import MusicList from '@/components/music/MusicList.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import type { PlayHistoryItem, Track } from '@/types/music'

const PAGE_SIZE = 20
const BOTTOM_THRESHOLD_PX = 120

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const playerStore = usePlayerStore()

const tracks = ref<PlayHistoryItem[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const loadError = ref('')
const hasMore = ref(false)
const scrollContainer = ref<HTMLElement | null>(null)

const latestPlayedAtLabel = computed(() => {
  const latestTrack = tracks.value[0]
  if (!latestTrack) {
    return ''
  }
  return formatDateTime(latestTrack.playedAt)
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
  } else {
    loadingMore.value = true
  }

  try {
    const offset = reset ? 0 : tracks.value.length
    const response = await getPlayHistory(PAGE_SIZE, offset)

    hasMore.value = response.hasMore
    tracks.value = reset ? response.items : [...tracks.value, ...response.items]
    loadError.value = ''
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      authStore.clearSession()
      await router.replace({
        name: 'Login',
        query: { redirect: route.fullPath },
      })
      return
    }

    if (error instanceof TypeError && /fetch/i.test(error.message)) {
      loadError.value = '网络请求失败，请检查后端服务后重试'
    } else {
      loadError.value = error instanceof Error ? error.message : '历史播放加载失败，请稍后重试'
    }
    if (reset) {
      tracks.value = []
      hasMore.value = false
    }
  } finally {
    loading.value = false
    loadingMore.value = false
    void nextTick().then(tryLoadMoreIfNeeded)
  }
}

function isNearBottom(container: HTMLElement): boolean {
  const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight
  return distanceToBottom <= BOTTOM_THRESHOLD_PX
}

function tryLoadMoreIfNeeded(): void {
  const container = scrollContainer.value
  if (!container) {
    return
  }
  if (loading.value || loadingMore.value || loadError.value || !hasMore.value) {
    return
  }
  if (isNearBottom(container)) {
    void loadHistory(false)
  }
}

function handleScroll(): void {
  tryLoadMoreIfNeeded()
}

function bindScrollContainer(): void {
  const container = document.querySelector('.main-layout__scroll')
  if (!(container instanceof HTMLElement)) {
    return
  }
  scrollContainer.value = container
  container.addEventListener('scroll', handleScroll, { passive: true })
}

function unbindScrollContainer(): void {
  if (!scrollContainer.value) {
    return
  }
  scrollContainer.value.removeEventListener('scroll', handleScroll)
  scrollContainer.value = null
}

function handlePlay(track: Track): void {
  void playerStore.playTrack(track, tracks.value)
}

onMounted(() => {
  bindScrollContainer()
  void loadHistory(true)
})

onBeforeUnmount(() => {
  unbindScrollContainer()
})
</script>

<template>
  <div class="history-page">
    <header class="history-page__hero">
      <h1 class="history-page__title">历史播放</h1>
      <p class="history-page__subtitle">按最近播放时间倒序展示你听过的歌曲</p>
      <p v-if="latestPlayedAtLabel" class="history-page__latest">
        最近播放：{{ latestPlayedAtLabel }}
      </p>
    </header>

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

    <MusicList title="最近播放" :tracks="tracks" :loading="loading" @play="handlePlay" />

    <div v-if="loadingMore" class="history-page__auto-loading">正在加载更多...</div>

    <div v-else-if="!loading && !loadError && hasMore" class="history-page__auto-load-tip">
      继续下滑可自动加载更多
    </div>

    <p v-if="!loading && tracks.length > 0" class="history-page__summary">
      已加载 {{ tracks.length }} 首
    </p>
  </div>
</template>

<style scoped>
.history-page {
  padding: 0.5rem 0;
  color: #1a2e1a;
}

.history-page__hero {
  margin-bottom: 2rem;
}

.history-page__title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #1d6f46, #4caf7d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.history-page__subtitle {
  color: rgba(0, 0, 0, 0.45);
  margin: 0;
  font-size: 0.9rem;
}

.history-page__latest {
  margin: 0.45rem 0 0;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.38);
}

.history-page__error {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(209, 77, 77, 0.3);
  border-radius: 8px;
  background: rgba(255, 230, 230, 0.5);
  color: #8a2b2b;
  font-size: 0.85rem;
}

.history-page__retry {
  border: none;
  border-radius: 6px;
  padding: 0.35rem 0.75rem;
  background: #1a2e1a;
  color: #fff;
  cursor: pointer;
  font-size: 0.78rem;
}

.history-page__retry:disabled {
  cursor: not-allowed;
  opacity: 0.72;
}

.history-page__auto-loading,
.history-page__auto-load-tip {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 1rem;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.45);
}

.history-page__summary {
  margin: 0.75rem 0 0;
  text-align: center;
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.35);
}
</style>
