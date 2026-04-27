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
  two_tower: '双塔候选',
  content_cold_start: '近期偏好',
  global_hot: '热门兜底',
}

const strategyDescriptionMap: Record<RecommendationStrategy, string> = {
  two_tower: '基于用户与歌曲向量召回的候选结果。',
  content_cold_start: '基于近期收听与偏好特征生成的候选结果。',
  global_hot: '当前未命中个性化缓存，已切换到热门兜底。',
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
        <h1 class="recommend-page__title">把推荐拆成可点、可听、可解释的两段</h1>
        <p class="recommend-page__subtitle">
          顶部卡片负责进入感，中部展示双塔候选，底部呈现近期偏好推荐。
        </p>
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
        <span class="recommend-page__entry-tag">猜你喜欢</span>
        <strong>双塔候选</strong>
        <p>进入后直接查看由用户行为向量召回的一组音乐，适合快速点播。</p>
        <span class="recommend-page__entry-foot"
          >{{ personalizedTracks.length || PAGE_SIZE }} 首候选</span
        >
      </button>

      <button
        class="recommend-page__entry-card recommend-page__entry-card--secondary"
        @click="scrollToSection('content-section')"
      >
        <span class="recommend-page__entry-tag">流派探索</span>
        <strong>近期偏好推荐</strong>
        <p>基于最近收听与内容相似度生成的推荐列表，适合继续深挖同类音乐。</p>
        <span class="recommend-page__entry-foot"
          >{{ contentTracks.length || PAGE_SIZE }} 首候选</span
        >
      </button>
    </section>

    <section id="personalized-section" class="recommend-page__section">
      <div class="recommend-page__section-head">
        <div>
          <p class="recommend-page__section-eyebrow">双塔结果</p>
          <h2 class="recommend-page__section-title">为你定制的单曲</h2>
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
          <p class="recommend-page__section-eyebrow">近期偏好</p>
          <h2 class="recommend-page__section-title">基于近期喜好的推荐</h2>
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
  gap: 1.2rem;
  padding: 0.25rem 0 0.75rem;
  color: #163025;
}

.recommend-page__hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.recommend-page__eyebrow,
.recommend-page__section-eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.76rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(15, 23, 42, 0.45);
}

.recommend-page__title {
  margin: 0;
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  letter-spacing: -0.04em;
  line-height: 1.08;
}

.recommend-page__subtitle,
.recommend-page__section-subtitle {
  margin: 0.7rem 0 0;
  color: rgba(15, 23, 42, 0.56);
  font-size: 0.94rem;
  max-width: 54rem;
}

.recommend-page__refresh {
  border: none;
  border-radius: 999px;
  padding: 0.7rem 1rem;
  background: linear-gradient(135deg, #0f6b47, #16a34a);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 12px 24px rgba(16, 185, 129, 0.24);
}

.recommend-page__entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.recommend-page__entry-card {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 1rem;
  border-radius: 22px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  text-align: left;
  color: #163025;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.recommend-page__entry-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 34px rgba(11, 30, 22, 0.12);
}

.recommend-page__entry-card strong {
  font-size: 1.2rem;
}

.recommend-page__entry-card p {
  margin: 0;
  color: rgba(15, 23, 42, 0.55);
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
  color: rgba(15, 23, 42, 0.42);
}

.recommend-page__entry-foot {
  color: rgba(15, 23, 42, 0.42);
}

.recommend-page__entry-card--primary {
  background: linear-gradient(180deg, rgba(236, 253, 245, 0.98), rgba(214, 248, 231, 0.92));
}

.recommend-page__entry-card--secondary {
  background: linear-gradient(180deg, rgba(255, 250, 235, 0.98), rgba(255, 241, 196, 0.88));
}

.recommend-page__section {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem;
  border-radius: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 16px 42px rgba(11, 30, 22, 0.06);
}

.recommend-page__section-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
}

.recommend-page__section-title {
  margin: 0;
  font-size: 1.15rem;
}

.recommend-page__section-chip {
  padding: 0.5rem 0.8rem;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
  color: #0f6b47;
}

.recommend-page__section-chip--soft {
  background: rgba(245, 158, 11, 0.12);
  color: #8a5a00;
}

.recommend-page__error {
  padding: 0.8rem 0.95rem;
  border-radius: 16px;
  border: 1px solid rgba(220, 85, 85, 0.18);
  color: #9a2d2d;
  background: rgba(255, 235, 235, 0.72);
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
