<script setup lang="ts">
/**
 * RecommendPage — 个性推荐主页面
 *
 * 使用双卡入口 + 双列表的混合布局，分别承接双塔候选与近期偏好推荐。
 */

import { computed, onMounted, ref } from 'vue'

import { HttpError } from '@/api/http'
import { getContentRecommendations, getPersonalizedRecommendations } from '@/api/recommendation'
import MusicList from '@/components/music/MusicList.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import type { RecommendationStrategy, Track } from '@/types/music'

const PAGE_SIZE = 16

const authStore = useAuthStore()
const playerStore = usePlayerStore()

const personalizedTracks = ref<Track[]>([])
const contentTracks = ref<Track[]>([])
const personalizedStrategy = ref<RecommendationStrategy | null>(null)
const contentStrategy = ref<RecommendationStrategy | null>(null)
const personalizedLoading = ref(true)
const contentLoading = ref(true)
const personalizedLoadingMore = ref(false)
const contentLoadingMore = ref(false)
const personalizedHasMore = ref(false)
const contentHasMore = ref(false)
const personalizedError = ref('')
const contentError = ref('')

let personalizedCache: {
  tracks: Track[]
  strategy: RecommendationStrategy | null
  timestamp: number
} | null = null

let contentCache: {
  tracks: Track[]
  strategy: RecommendationStrategy | null
  timestamp: number
} | null = null

const CACHE_TTL_MS = 5 * 60 * 1000

const strategyLabelMap: Record<RecommendationStrategy, string> = {
  two_tower: '为你推荐',
  content_cold_start: '偏好扩展',
  global_hot: '热门补位',
}

const strategyDescriptionMap: Record<RecommendationStrategy, string> = {
  two_tower: '根据你的听歌习惯与相似人群偏好生成。',
  content_cold_start: '围绕近期收听与流派偏好继续扩展。',
  global_hot: '当前个性化暂未命中，已切换热门推荐。',
}

const personalizedLabel = computed(() => {
  if (!personalizedStrategy.value) {
    return '加载中'
  }
  return strategyLabelMap[personalizedStrategy.value]
})

const personalizedDescription = computed(() => {
  if (!personalizedStrategy.value) {
    return '正在准备双塔候选列表。'
  }
  return strategyDescriptionMap[personalizedStrategy.value]
})

const contentLabel = computed(() => {
  if (!contentStrategy.value) {
    return '加载中'
  }
  return strategyLabelMap[contentStrategy.value]
})

const contentDescription = computed(() => {
  if (!contentStrategy.value) {
    return '正在准备近期偏好列表。'
  }
  return strategyDescriptionMap[contentStrategy.value]
})

function isCacheValid(timestamp: number): boolean {
  return Date.now() - timestamp < CACHE_TTL_MS
}

async function loadPersonalized(force = false): Promise<void> {
  if (!force && personalizedCache && isCacheValid(personalizedCache.timestamp)) {
    personalizedTracks.value = personalizedCache.tracks
    personalizedStrategy.value = personalizedCache.strategy
    personalizedHasMore.value = personalizedCache.tracks.length >= PAGE_SIZE
    personalizedLoading.value = false
    return
  }

  personalizedLoading.value = true
  personalizedError.value = ''

  try {
    const response = await getPersonalizedRecommendations(PAGE_SIZE, 0)
    personalizedTracks.value = response.items
    personalizedStrategy.value = response.strategy
    personalizedHasMore.value =
      response.items.length >= PAGE_SIZE || response.total > response.items.length
    personalizedCache = {
      tracks: response.items,
      strategy: response.strategy,
      timestamp: Date.now(),
    }
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      authStore.clearSession()
      return
    }
    personalizedError.value =
      error instanceof Error ? error.message : '双塔候选加载失败，请稍后重试'
    personalizedTracks.value = []
    personalizedStrategy.value = null
  } finally {
    personalizedLoading.value = false
  }
}

async function loadMorePersonalized(): Promise<void> {
  if (personalizedLoading.value || personalizedLoadingMore.value || !personalizedHasMore.value) {
    return
  }

  personalizedLoadingMore.value = true
  personalizedError.value = ''

  try {
    const response = await getPersonalizedRecommendations(
      PAGE_SIZE,
      personalizedTracks.value.length,
    )
    personalizedTracks.value = [...personalizedTracks.value, ...response.items]
    personalizedStrategy.value = response.strategy
    personalizedHasMore.value =
      response.items.length >= PAGE_SIZE || response.total > personalizedTracks.value.length
    personalizedCache = {
      tracks: [...personalizedTracks.value],
      strategy: response.strategy,
      timestamp: Date.now(),
    }
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      authStore.clearSession()
      return
    }
    personalizedError.value =
      error instanceof Error ? error.message : '双塔候选加载失败，请稍后重试'
  } finally {
    personalizedLoadingMore.value = false
  }
}

async function loadContent(force = false): Promise<void> {
  if (!force && contentCache && isCacheValid(contentCache.timestamp)) {
    contentTracks.value = contentCache.tracks
    contentStrategy.value = contentCache.strategy
    contentHasMore.value = contentCache.tracks.length >= PAGE_SIZE
    contentLoading.value = false
    return
  }

  contentLoading.value = true
  contentError.value = ''

  try {
    const response = await getContentRecommendations(PAGE_SIZE, 0)
    contentTracks.value = response.items
    contentStrategy.value = response.strategy
    contentHasMore.value =
      response.items.length >= PAGE_SIZE || response.total > response.items.length
    contentCache = {
      tracks: response.items,
      strategy: response.strategy,
      timestamp: Date.now(),
    }
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      authStore.clearSession()
      return
    }
    contentError.value = error instanceof Error ? error.message : '近期偏好推荐加载失败，请稍后重试'
    contentTracks.value = []
    contentStrategy.value = null
  } finally {
    contentLoading.value = false
  }
}

async function loadMoreContent(): Promise<void> {
  if (contentLoading.value || contentLoadingMore.value || !contentHasMore.value) {
    return
  }

  contentLoadingMore.value = true
  contentError.value = ''

  try {
    const response = await getContentRecommendations(PAGE_SIZE, contentTracks.value.length)
    contentTracks.value = [...contentTracks.value, ...response.items]
    contentStrategy.value = response.strategy
    contentHasMore.value =
      response.items.length >= PAGE_SIZE || response.total > contentTracks.value.length
    contentCache = {
      tracks: [...contentTracks.value],
      strategy: response.strategy,
      timestamp: Date.now(),
    }
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      authStore.clearSession()
      return
    }
    contentError.value = error instanceof Error ? error.message : '近期偏好推荐加载失败，请稍后重试'
  } finally {
    contentLoadingMore.value = false
  }
}

function refreshRecommendations(): void {
  personalizedCache = null
  contentCache = null
  void loadPersonalized(true)
  void loadContent(true)
}

function handlePersonalizedPlay(track: Track): void {
  void playerStore.playTrack(track, personalizedTracks.value)
}

function handleContentPlay(track: Track): void {
  void playerStore.playTrack(track, contentTracks.value)
}

function scrollToSection(sectionId: string): void {
  document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  void loadPersonalized()
  void loadContent()
})
</script>

<template>
  <div class="recommend-page">
    <header class="recommend-page__hero">
      <div>
        <p class="recommend-page__eyebrow">个性推荐</p>
        <h1 class="recommend-page__title">为你定制的推荐</h1>
        <p class="recommend-page__subtitle">基于你的播放历史与偏好生成，随时可刷新。</p>
      </div>

      <button
        class="recommend-page__refresh"
        :disabled="personalizedLoading || contentLoading"
        @click="refreshRecommendations"
      >
        {{ personalizedLoading || contentLoading ? '刷新中...' : '刷新推荐' }}
      </button>
    </header>

    <section class="recommend-page__entry-grid">
      <button
        class="recommend-page__entry-card recommend-page__entry-card--primary"
        @click="scrollToSection('personalized-section')"
      >
        <span class="recommend-page__entry-tag">推荐流</span>
        <strong>猜你喜欢</strong>
        <p>直接查看为你准备的候选歌曲，适合快速点播。</p>
        <span class="recommend-page__entry-foot"
          >{{ personalizedTracks.length || PAGE_SIZE }} 首候选</span
        >
      </button>

      <button
        class="recommend-page__entry-card recommend-page__entry-card--secondary"
        @click="scrollToSection('content-section')"
      >
        <span class="recommend-page__entry-tag">偏好扩展</span>
        <strong>继续探索</strong>
        <p>围绕近期收听继续扩展，适合深挖同类音乐。</p>
        <span class="recommend-page__entry-foot"
          >{{ contentTracks.length || PAGE_SIZE }} 首候选</span
        >
      </button>
    </section>

    <section id="personalized-section" class="recommend-page__section">
      <div class="recommend-page__section-head">
        <div>
          <p class="recommend-page__section-eyebrow">推荐流</p>
          <h2 class="recommend-page__section-title">猜你喜欢</h2>
          <p class="recommend-page__section-subtitle">{{ personalizedDescription }}</p>
        </div>
        <span class="recommend-page__section-chip">{{ personalizedLabel }}</span>
      </div>

      <div v-if="personalizedError" class="recommend-page__error">
        <span>{{ personalizedError }}</span>
      </div>

      <MusicList
        :title="`为你定制的单曲 · ${personalizedTracks.length} 首`"
        :tracks="personalizedTracks"
        :loading="personalizedLoading"
        :has-more="personalizedHasMore"
        :loading-more="personalizedLoadingMore"
        @play="handlePersonalizedPlay"
        @load-more="loadMorePersonalized"
      />
    </section>

    <section id="content-section" class="recommend-page__section">
      <div class="recommend-page__section-head">
        <div>
          <p class="recommend-page__section-eyebrow">偏好扩展</p>
          <h2 class="recommend-page__section-title">继续探索</h2>
          <p class="recommend-page__section-subtitle">{{ contentDescription }}</p>
        </div>
        <span class="recommend-page__section-chip recommend-page__section-chip--soft">{{
          contentLabel
        }}</span>
      </div>

      <div v-if="contentError" class="recommend-page__error">
        <span>{{ contentError }}</span>
      </div>

      <MusicList
        :title="`基于近期喜好的推荐 · ${contentTracks.length} 首`"
        :tracks="contentTracks"
        :loading="contentLoading"
        :has-more="contentHasMore"
        :loading-more="contentLoadingMore"
        @play="handleContentPlay"
        @load-more="loadMoreContent"
      />
    </section>
  </div>
</template>

<style scoped>
.recommend-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.5rem 0 1rem;
  color: var(--ink-900);
}

.recommend-page__hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.1rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
}

.recommend-page__eyebrow,
.recommend-page__section-eyebrow {
  margin: 0 0 0.5rem;
  font-size: 0.76rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-300);
}

.recommend-page__title {
  margin: 0;
  font-size: clamp(1.7rem, 3.6vw, 2.4rem);
  letter-spacing: -0.03em;
  line-height: 1.08;
}

.recommend-page__subtitle,
.recommend-page__section-subtitle {
  margin: 0.5rem 0 0;
  color: var(--ink-500);
  font-size: 0.92rem;
  max-width: 54rem;
}

.recommend-page__refresh {
  border: 1px solid var(--surface-border);
  border-radius: 999px;
  padding: 0.5rem 1rem;
  background: var(--surface-1);
  color: var(--ink-700);
  font-weight: 600;
  box-shadow: none;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease;
}

.recommend-page__refresh:hover:not(:disabled) {
  background: #ffffff;
  box-shadow: var(--shadow-soft);
  transform: translateY(-1px);
}

.recommend-page__entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

.recommend-page__entry-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--surface-border);
  border-left: 3px solid transparent;
  background: var(--surface-0);
  text-align: left;
  color: var(--ink-900);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.recommend-page__entry-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-strong);
}

.recommend-page__entry-card strong {
  font-size: 1.2rem;
}

.recommend-page__entry-card p {
  margin: 0;
  color: var(--ink-500);
  font-size: 0.86rem;
  line-height: 1.55;
}

.recommend-page__entry-tag,
.recommend-page__entry-foot,
.recommend-page__section-chip {
  font-size: 0.74rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.recommend-page__entry-tag {
  color: var(--ink-300);
}

.recommend-page__entry-foot {
  color: var(--ink-300);
}

.recommend-page__entry-card--primary {
  border-left-color: var(--accent-600);
}

.recommend-page__entry-card--secondary {
  border-left-color: rgba(15, 23, 42, 0.3);
}

.recommend-page__section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
}

.recommend-page__section-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
}

.recommend-page__section-title {
  margin: 0;
  font-size: 1.1rem;
}

.recommend-page__section-chip {
  padding: 0.5rem 0.8rem;
  border-radius: 999px;
  background: var(--surface-1);
  color: var(--ink-700);
}

.recommend-page__section-chip--soft {
  background: var(--surface-2);
  color: var(--ink-700);
}

.recommend-page__error {
  padding: 0.75rem 0.9rem;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(181, 63, 75, 0.2);
  color: #9b2f3a;
  background: rgba(255, 235, 238, 0.7);
}

@media (max-width: 900px) {
  .recommend-page__hero,
  .recommend-page__section-head,
  .recommend-page__entry-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .recommend-page__hero {
    display: grid;
  }
}
</style>
