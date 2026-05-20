<script setup lang="ts">
/**
 * HomePage — 首页
 *
 * 负责展示用户画像、最近播放和两个高亮入口。
 */

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getLatestPlayHistory, getPlayHistory } from '@/api/history'
import { getListeningInsights } from '@/api/user'
import defaultCover from '@/assets/images/default-cover.svg'
import PreferenceRadarChart from '@/components/music/PreferenceRadarChart.vue'
import TrackRail from '@/components/music/TrackRail.vue'
import { useAuthStore } from '@/stores/auth'
import { useCoverStore } from '@/stores/cover'
import { usePlayerStore } from '@/stores/player'
import type { GenrePreferenceItem, PlayHistoryItem, Track } from '@/types/music'

const router = useRouter()
const authStore = useAuthStore()
const playerStore = usePlayerStore()
const coverStore = useCoverStore()

const insights = ref<GenrePreferenceItem[]>([])
const totalPlays = ref(0)
const recentTracks = ref<PlayHistoryItem[]>([])
const latestTrack = ref<PlayHistoryItem | null>(null)
const loadingInsights = ref(true)
const loadingRecent = ref(true)
const loadError = ref('')

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) {
    return '早上好'
  }
  if (hour < 18) {
    return '下午好'
  }
  return '晚上好'
})

const displayName = computed(() => authStore.user?.username ?? '听歌人')

const insightSummary = computed(() => {
  if (insights.value.length === 0) {
    return '系统会在你播放一段时间后自动生成偏好雷达图。'
  }
  return `基于最近 ${totalPlays.value} 次播放生成 ${insights.value.length} 个高频流派维度。`
})

async function loadHomeData(): Promise<void> {
  loadError.value = ''
  loadingInsights.value = true
  loadingRecent.value = true

  try {
    const [insightsResponse, historyResponse, latestResponse] = await Promise.all([
      getListeningInsights(),
      getPlayHistory(8, 0),
      getLatestPlayHistory(),
    ])

    insights.value = insightsResponse.items
    totalPlays.value = insightsResponse.totalPlays
    recentTracks.value = historyResponse.items
    latestTrack.value = latestResponse
    if (latestResponse) {
      void coverStore.resolveCovers([latestResponse.id])
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '首页数据加载失败，请稍后重试'
  } finally {
    loadingInsights.value = false
    loadingRecent.value = false
  }
}

function openDailyExclusive(): void {
  void router.push({ name: 'Recommend' })
}

function openTrending(): void {
  void router.push({ name: 'Discover' })
}

function handlePlay(track: Track): void {
  void playerStore.playTrack(track, recentTracks.value)
}

function coverUrl(track: Track | null): string {
  if (!track) return defaultCover
  const cached = coverStore.getCoverUrl(track.id)
  if (cached) return cached
  return track.coverUrl?.trim() || defaultCover
}

onMounted(() => {
  void loadHomeData()
})
</script>

<template>
  <div class="home-page">
    <section class="home-page__hero">
      <div class="home-page__hero-copy">
        <p class="home-page__eyebrow">FlowBeat</p>
        <h1 class="home-page__greeting">
          {{ greeting }}，{{ displayName }}
          <span class="home-page__greeting-mark">🎵</span>
        </h1>
        <p class="home-page__subtitle">把你的听歌画像、最近播放和推荐入口集中在同一视线里。</p>
      </div>

      <div class="home-page__hero-actions">
        <button
          class="home-page__highlight-card home-page__highlight-card--primary"
          @click="openDailyExclusive"
        >
          <strong>专属推荐流</strong>
          <span>直达双塔候选与近期偏好。</span>
        </button>

        <button
          class="home-page__highlight-card home-page__highlight-card--secondary"
          @click="openTrending"
        >
          <strong>今日热榜</strong>
          <span>浏览热门、新歌与流派入口。</span>
        </button>
      </div>
    </section>

    <section class="home-page__content-grid">
      <div class="home-page__radar">
        <PreferenceRadarChart
          :items="insights"
          title="偏好雷达"
          :loading="loadingInsights"
          :subtitle="insightSummary"
        />
      </div>

      <aside class="home-page__side-panel">
        <button
          class="home-page__resume-card"
          type="button"
          :class="{ 'home-page__resume-card--empty': !latestTrack }"
          :disabled="!latestTrack"
          @click="latestTrack && handlePlay(latestTrack)"
        >
          <div class="home-page__resume-cover">
            <img :src="coverUrl(latestTrack)" :alt="latestTrack?.name || '最近播放'" />
            <div class="home-page__resume-overlay">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          </div>
          <div class="home-page__resume-meta">
            <p class="home-page__panel-eyebrow">继续播放</p>
            <strong class="home-page__resume-title">
              {{ latestTrack ? latestTrack.name : '还没有最近播放' }}
            </strong>
            <p class="home-page__resume-subtitle">
              {{ latestTrack ? latestTrack.artist : '听一首歌后，这里会自动帮你接回上次进度。' }}
            </p>
            <span v-if="latestTrack" class="home-page__resume-hint">悬停封面即可播放</span>
          </div>
        </button>

        <div class="home-page__panel-card home-page__panel-card--soft">
          <p class="home-page__panel-eyebrow">画像概览</p>
          <div class="home-page__metrics">
            <div>
              <strong>{{ totalPlays }}</strong>
              <span>总播放次数</span>
            </div>
            <div>
              <strong>{{ insights.length }}</strong>
              <span>高频流派</span>
            </div>
          </div>
          <p class="home-page__panel-note">
            {{ loadError || '雷达图会随着播放行为更新，帮助你快速理解自己的听歌轮廓。' }}
          </p>
        </div>
      </aside>
    </section>

    <TrackRail
      title="最近播放"
      subtitle="最近 8 首歌曲"
      :tracks="recentTracks"
      :loading="loadingRecent"
      layout="grid"
      :columns="8"
      empty-text="暂无最近播放记录"
      @play="handlePlay"
    />
  </div>
</template>

<style scoped>
.home-page {
  --home-gap: 1rem;
  --home-columns: minmax(0, 7fr) minmax(0, 5fr);

  display: flex;
  flex-direction: column;
  gap: var(--home-gap);
  padding: 0 0 1rem;
  color: var(--ink-900);
  min-width: 0; /* 允许 flex 收缩，防止撑破父容器 */
  overflow: hidden; /* 确保子内容不会溢出到视口外 */
  width: 100%;
}

.home-page__hero {
  display: grid;
  grid-template-columns: var(--home-columns);
  gap: var(--home-gap);
  align-items: stretch;
}

.home-page__hero-copy,
.home-page__hero-actions,
.home-page__panel-card {
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
}

.home-page__hero-copy {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem 1.25rem 0.9rem;
}

.home-page__eyebrow {
  margin: 0 0 0.5rem;
  font-size: 0.76rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-300);
}

.home-page__greeting {
  margin: 0;
  font-size: clamp(1.9rem, 3.6vw, 3rem);
  line-height: 1.05;
  letter-spacing: -0.03em;
}

.home-page__greeting-mark {
  font-size: 0.84em;
}

.home-page__subtitle {
  margin: 0.5rem 0 0;
  max-width: 100%;
  color: var(--ink-500);
  font-size: 0.95rem;
}

.home-page__hero-actions {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--home-gap);
  padding: 0;
  align-items: stretch;
}

.home-page__highlight-card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.85rem 0.95rem;
  border-radius: var(--radius-lg);
  color: var(--ink-900);
  text-align: left;
  border: 1px solid var(--surface-border);
  border-left: 3px solid transparent;
  background: var(--surface-0);
  height: 100%;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.home-page__highlight-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-strong);
}

.home-page__highlight-card strong {
  font-size: 1.12rem;
}

.home-page__highlight-card span:last-child {
  color: var(--ink-500);
  font-size: 0.84rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  overflow: hidden;
}

.home-page__highlight-tag,
.home-page__panel-eyebrow {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.home-page__highlight-tag {
  color: var(--ink-300);
}

.home-page__highlight-card--primary {
  border-left-color: var(--accent-600);
}

.home-page__highlight-card--secondary {
  border-left-color: rgba(15, 23, 42, 0.24);
}

.home-page__content-grid {
  display: grid;
  grid-template-columns: var(--home-columns);
  gap: var(--home-gap);
  align-items: start;
}

.home-page__radar {
  width: 100%;
}

.home-page__side-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.home-page__panel-card {
  padding: 0.85rem 0.95rem;
}

.home-page__panel-card--soft {
  background: var(--surface-0);
}

.home-page__panel-eyebrow {
  margin: 0 0 0.5rem;
  color: var(--ink-300);
}

.home-page__panel-title {
  display: block;
  font-size: 1.05rem;
}

.home-page__panel-subtitle,
.home-page__panel-note {
  margin: 0.35rem 0 0;
  color: var(--ink-500);
  font-size: 0.85rem;
  line-height: 1.55;
}

.home-page__metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin: 0.35rem 0 0.5rem;
}

.home-page__metrics div {
  padding: 0.75rem;
  border-radius: var(--radius-lg);
  background: var(--surface-1);
  border: 1px solid var(--surface-border);
}

.home-page__metrics strong {
  display: block;
  font-size: 1.35rem;
  color: var(--accent-600);
}

.home-page__metrics span {
  color: var(--ink-500);
  font-size: 0.78rem;
}

.home-page__resume-card {
  display: grid;
  grid-template-columns: 84px 1fr;
  gap: 0.5rem;
  align-items: center;
  padding: 0.85rem 0.95rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.home-page__resume-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-strong);
}

.home-page__resume-card:disabled {
  cursor: default;
  transform: none;
  box-shadow: none;
}

.home-page__resume-cover {
  position: relative;
  width: 84px;
  height: 84px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--surface-1);
}

.home-page__resume-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: filter 0.2s ease;
}

.home-page__resume-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(11, 15, 20, 0.45);
  opacity: 0;
  transition: opacity 0.2s ease;
  color: #ffffff;
}

.home-page__resume-overlay svg {
  width: 28px;
  height: 28px;
}

.home-page__resume-card:hover .home-page__resume-overlay {
  opacity: 1;
}

.home-page__resume-card:hover .home-page__resume-cover img {
  filter: brightness(0.85);
}

.home-page__resume-card--empty .home-page__resume-overlay {
  display: none;
}

.home-page__resume-card--empty .home-page__resume-cover img {
  filter: grayscale(0.2) brightness(0.95);
}

.home-page__resume-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.home-page__resume-title {
  font-size: 1.05rem;
  color: var(--ink-900);
}

.home-page__resume-subtitle {
  margin: 0;
  color: var(--ink-500);
  font-size: 0.85rem;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.home-page__resume-hint {
  font-size: 0.72rem;
  color: var(--ink-300);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

@media (max-width: 1080px) {
  .home-page__hero,
  .home-page__content-grid {
    grid-template-columns: 1fr;
  }

  .home-page__hero-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .home-page__hero-actions,
  .home-page__metrics {
    grid-template-columns: 1fr;
  }

  .home-page__resume-card {
    grid-template-columns: 72px 1fr;
  }

  .home-page__resume-cover {
    width: 72px;
    height: 72px;
  }
}
</style>
