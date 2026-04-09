<script setup lang="ts">
/**
 * RecommendPage — 个性推荐主页面
 *
 * 展示个性化推荐结果，并标注当前命中的推荐策略。
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getPersonalizedRecommendations } from '@/api/recommendation'
import { HttpError } from '@/api/http'
import MusicList from '@/components/music/MusicList.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import type { RecommendationStrategy, Track } from '@/types/music'

const PAGE_SIZE = 20
const BOTTOM_THRESHOLD_PX = 120

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const playerStore = usePlayerStore()

const tracks = ref<Track[]>([])
const strategy = ref<RecommendationStrategy | null>(null)
const total = ref(0)
const loading = ref(true)
const loadingMore = ref(false)
const loadError = ref('')
const scrollContainer = ref<HTMLElement | null>(null)

const strategyLabelMap: Record<RecommendationStrategy, string> = {
  two_tower: '双塔个性化',
  content_cold_start: '偏好冷启动',
  global_hot: '全局热门兜底',
}

const strategyDescriptionMap: Record<RecommendationStrategy, string> = {
  two_tower: '基于用户与歌曲向量召回，优先返回高相关候选。',
  content_cold_start: '基于注册偏好流派进行内容匹配，适用于冷启动或主策略未命中。',
  global_hot: '当前未命中个性化结果，系统已自动降级到全站热门榜单。',
}

const strategyTagClass = computed(() => {
  if (strategy.value === 'two_tower') {
    return 'recommend-page__strategy-tag--primary'
  }
  if (strategy.value === 'content_cold_start') {
    return 'recommend-page__strategy-tag--secondary'
  }
  return 'recommend-page__strategy-tag--fallback'
})

const strategyLabel = computed(() => {
  if (!strategy.value) {
    return '加载中'
  }
  return strategyLabelMap[strategy.value]
})

const strategyDescription = computed(() => {
  if (!strategy.value) {
    return '正在获取推荐来源...'
  }
  return strategyDescriptionMap[strategy.value]
})

const hasMore = computed(() => tracks.value.length < total.value)

const loadedSummary = computed(() => {
  if (total.value <= 0) {
    return ''
  }
  return `已加载 ${tracks.value.length} / ${total.value} 首`
})

async function loadRecommendations(reset = false): Promise<void> {
  if (!reset && (!hasMore.value || loading.value || loadingMore.value)) {
    return
  }

  if (reset) {
    loading.value = true
    tracks.value = []
    total.value = 0
  } else {
    loadingMore.value = true
  }

  try {
    const offset = reset ? 0 : tracks.value.length
    const response = await getPersonalizedRecommendations(PAGE_SIZE, offset)

    strategy.value = response.strategy
    total.value = response.total
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
      loadError.value = error instanceof Error ? error.message : '个性推荐加载失败，请稍后重试'
    }

    if (reset) {
      tracks.value = []
      total.value = 0
      strategy.value = null
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
    void loadRecommendations(false)
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

function refreshRecommendations(): void {
  void loadRecommendations(true)
}

onMounted(() => {
  bindScrollContainer()
  void loadRecommendations(true)
})

onBeforeUnmount(() => {
  unbindScrollContainer()
})
</script>

<template>
  <div class="recommend-page">
    <header class="recommend-page__hero">
      <div>
        <h1 class="recommend-page__title">个性推荐</h1>
        <p class="recommend-page__subtitle">
          按你的偏好与行为生成推荐，并在未命中时自动降级保证可用性
        </p>
      </div>
      <button
        class="recommend-page__refresh"
        :disabled="loading || loadingMore"
        @click="refreshRecommendations"
      >
        {{ loading ? '刷新中...' : '刷新推荐' }}
      </button>
    </header>

    <section class="recommend-page__strategy-card" aria-live="polite">
      <p class="recommend-page__strategy-caption">当前命中策略</p>
      <div class="recommend-page__strategy-content">
        <span class="recommend-page__strategy-tag" :class="strategyTagClass">
          {{ strategyLabel }}
        </span>
        <p class="recommend-page__strategy-desc">{{ strategyDescription }}</p>
      </div>
    </section>

    <div v-if="loadError" class="recommend-page__error">
      <span>{{ loadError }}</span>
      <button
        class="recommend-page__retry"
        :disabled="loading || loadingMore"
        @click="refreshRecommendations"
      >
        {{ loading ? '重试中...' : '重试' }}
      </button>
    </div>

    <MusicList title="为你推荐" :tracks="tracks" :loading="loading" @play="handlePlay" />

    <div v-if="loadingMore" class="recommend-page__auto-loading">正在加载更多...</div>

    <div v-else-if="!loading && !loadError && hasMore" class="recommend-page__auto-load-tip">
      继续下滑可自动加载更多
    </div>

    <p v-if="!loading && tracks.length > 0" class="recommend-page__summary">{{ loadedSummary }}</p>

    <p v-else-if="!loading && !loadError && tracks.length === 0" class="recommend-page__empty-tip">
      当前暂无可展示推荐，请稍后刷新重试
    </p>
  </div>
</template>

<style scoped>
.recommend-page {
  padding: 0.5rem 0;
  color: #1a2e1a;
}

.recommend-page__hero {
  margin-bottom: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.recommend-page__title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #1a7a67, #2bb673);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.recommend-page__subtitle {
  color: rgba(0, 0, 0, 0.45);
  margin: 0;
  font-size: 0.9rem;
  max-width: 640px;
}

.recommend-page__refresh {
  border: none;
  border-radius: 999px;
  padding: 0.48rem 0.95rem;
  background: linear-gradient(135deg, #1d6f46, #4caf7d);
  color: #fff;
  font-size: 0.8rem;
  font-weight: 600;
  transition: transform 0.18s ease;
}

.recommend-page__refresh:hover:not(:disabled) {
  transform: translateY(-1px);
}

.recommend-page__refresh:disabled {
  opacity: 0.68;
  cursor: not-allowed;
}

.recommend-page__strategy-card {
  margin-bottom: 1.25rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  background: radial-gradient(circle at 0% 0%, rgba(76, 175, 125, 0.14), transparent 45%), #ffffff;
}

.recommend-page__strategy-caption {
  margin: 0 0 0.45rem;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(0, 0, 0, 0.38);
}

.recommend-page__strategy-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.recommend-page__strategy-tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.24rem 0.65rem;
  font-size: 0.76rem;
  font-weight: 600;
}

.recommend-page__strategy-tag--primary {
  color: #125f3c;
  background: rgba(44, 184, 115, 0.18);
}

.recommend-page__strategy-tag--secondary {
  color: #0b6174;
  background: rgba(58, 156, 181, 0.17);
}

.recommend-page__strategy-tag--fallback {
  color: #7a4e00;
  background: rgba(244, 183, 63, 0.22);
}

.recommend-page__strategy-desc {
  margin: 0;
  color: rgba(0, 0, 0, 0.55);
  font-size: 0.82rem;
}

.recommend-page__error {
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

.recommend-page__retry {
  border: none;
  border-radius: 6px;
  padding: 0.35rem 0.75rem;
  background: #1a2e1a;
  color: #fff;
  cursor: pointer;
  font-size: 0.78rem;
}

.recommend-page__retry:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.recommend-page__auto-loading,
.recommend-page__auto-load-tip {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 1rem;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.45);
}

.recommend-page__summary {
  margin: 0.75rem 0 0;
  text-align: center;
  font-size: 0.8rem;
  color: rgba(0, 0, 0, 0.45);
}

.recommend-page__empty-tip {
  margin: 1rem 0 0;
  text-align: center;
  font-size: 0.82rem;
  color: rgba(0, 0, 0, 0.42);
}

@media (max-width: 768px) {
  .recommend-page__hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
