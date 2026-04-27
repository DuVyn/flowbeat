<script setup lang="ts">
/**
 * SearchPage — 搜索结果页
 *
 * 通过路由查询参数 q 读取关键词，并调用后端歌曲搜索接口。
 */

import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { HttpError } from '@/api/http'
import { searchSongs } from '@/api/song'
import MusicList from '@/components/music/MusicList.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import type { Track } from '@/types/music'

const PAGE_SIZE = 20

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const playerStore = usePlayerStore()

const keyword = ref('')
const tracks = ref<Track[]>([])
const hasMore = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const loadError = ref('')

const hasKeyword = computed(() => keyword.value.length > 0)

const resultSummary = computed(() => {
  if (!hasKeyword.value) {
    return ''
  }
  if (tracks.value.length <= 0) {
    return ''
  }
  if (hasMore.value) {
    return `已加载 ${tracks.value.length} 首，仍有更多结果可继续加载`
  }
  return `共找到 ${tracks.value.length} 首结果`
})

function parseKeywordFromRoute(): string {
  const rawKeyword = route.query.q
  if (Array.isArray(rawKeyword)) {
    return String(rawKeyword[0] ?? '').trim()
  }
  return typeof rawKeyword === 'string' ? rawKeyword.trim() : ''
}

async function loadResults(reset: boolean): Promise<void> {
  if (!hasKeyword.value) {
    tracks.value = []
    hasMore.value = false
    loadError.value = ''
    return
  }

  if (!reset && (!hasMore.value || loading.value || loadingMore.value)) {
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
    const response = await searchSongs(keyword.value, PAGE_SIZE, offset)
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
      loadError.value = '网络请求失败，请检查后端服务是否可用'
    } else {
      loadError.value = error instanceof Error ? error.message : '搜索失败，请稍后重试'
    }

    if (reset) {
      tracks.value = []
      hasMore.value = false
    }
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

function handlePlay(track: Track): void {
  void playerStore.playTrack(track, tracks.value)
}

function refreshResults(): void {
  void loadResults(true)
}

function loadMoreResults(): void {
  if (loading.value || loadingMore.value || loadError.value || !hasMore.value) {
    return
  }
  void loadResults(false)
}

watch(
  () => route.query.q,
  () => {
    keyword.value = parseKeywordFromRoute()
    void loadResults(true)
  },
  { immediate: true },
)
</script>

<template>
  <div class="search-page">
    <header class="search-page__hero">
      <h1 class="search-page__title">搜索</h1>
      <p class="search-page__subtitle">按歌曲名、歌手或歌曲 ID 检索音乐</p>
    </header>

    <section v-if="!hasKeyword" class="search-page__empty-query">
      <p class="search-page__empty-title">请输入关键词开始搜索</p>
      <p class="search-page__empty-hint">可在顶部搜索框输入后按回车，例如：周杰伦 / love / 12345</p>
    </section>

    <div v-else class="search-page__result">
      <section class="search-page__query-card">
        <p class="search-page__query-caption">当前关键词</p>
        <h2 class="search-page__query-value">{{ keyword }}</h2>
      </section>

      <div v-if="loadError" class="search-page__error">
        <span>{{ loadError }}</span>
        <button
          class="search-page__retry"
          :disabled="loading || loadingMore"
          @click="refreshResults"
        >
          {{ loading ? '重试中...' : '重试' }}
        </button>
      </div>

      <MusicList
        title="搜索结果"
        :tracks="tracks"
        :loading="loading"
        :has-more="hasMore"
        :loading-more="loadingMore"
        @play="handlePlay"
        @load-more="loadMoreResults"
      />

      <p v-if="!loading && !loadError && tracks.length === 0" class="search-page__no-result">
        未找到与“{{ keyword }}”相关的歌曲，请尝试更换关键词
      </p>

      <p v-if="!loading && !loadError && tracks.length > 0" class="search-page__summary">
        {{ resultSummary }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.search-page {
  padding: 0.5rem 0;
  color: #1a2e1a;
}

.search-page__hero {
  margin-bottom: 1.25rem;
}

.search-page__title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #1b6b8a, #25a58f);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.search-page__subtitle {
  color: rgba(0, 0, 0, 0.45);
  margin: 0;
  font-size: 0.9rem;
}

.search-page__empty-query {
  margin-top: 1rem;
  padding: 1.1rem 1.2rem;
  border: 1px dashed rgba(27, 107, 138, 0.35);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(37, 165, 143, 0.08), rgba(27, 107, 138, 0.08));
}

.search-page__empty-title {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.65);
}

.search-page__empty-hint {
  margin: 0;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.45);
}

.search-page__query-card {
  margin-bottom: 1rem;
  padding: 0.9rem 1rem;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: radial-gradient(circle at 0% 0%, rgba(37, 165, 143, 0.13), transparent 45%), #ffffff;
}

.search-page__query-caption {
  margin: 0 0 0.45rem;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(0, 0, 0, 0.38);
}

.search-page__query-value {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 650;
  letter-spacing: 0.01em;
  color: #1a2e1a;
}

.search-page__error {
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

.search-page__retry {
  border: none;
  border-radius: 999px;
  padding: 0.45rem 0.9rem;
  color: #ffffff;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 600;
}

.search-page__retry {
  background: #1a2e1a;
}

.search-page__retry:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.search-page__auto-loading,
.search-page__auto-load-tip {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 1rem;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.45);
}

.search-page__no-result,
.search-page__summary {
  margin: 0.9rem 0 0;
  text-align: center;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.46);
}
</style>
