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
import PreferenceRadarChart from '@/components/music/PreferenceRadarChart.vue'
import TrackRail from '@/components/music/TrackRail.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import type { GenrePreferenceItem, PlayHistoryItem, Track } from '@/types/music'

const router = useRouter()
const authStore = useAuthStore()
const playerStore = usePlayerStore()

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

onMounted(() => {
  void loadHomeData()
})
</script>

<template>
  <div class="home-page">
    <section class="home-page__hero">
      <div class="home-page__hero-copy">
        <p class="home-page__eyebrow">FlowBeat 首页</p>
        <h1 class="home-page__greeting">
          {{ greeting }}，{{ displayName }}
          <span class="home-page__greeting-mark">🎵</span>
        </h1>
        <p class="home-page__subtitle">
          这里会优先展示你的听歌画像、最近播放和两个最快进入推荐的入口。
        </p>
      </div>

      <div class="home-page__hero-actions">
        <button
          class="home-page__highlight-card home-page__highlight-card--primary"
          @click="openDailyExclusive"
        >
          <span class="home-page__highlight-tag">推荐入口</span>
          <strong>开启每日专属</strong>
          <span>直接进入个性推荐，查看双塔候选与近期偏好。</span>
        </button>

        <button
          class="home-page__highlight-card home-page__highlight-card--secondary"
          @click="openTrending"
        >
          <span class="home-page__highlight-tag">探索入口</span>
          <strong>探索今日热门</strong>
          <span>浏览全站热歌、流派导航和新歌速递。</span>
        </button>
      </div>
    </section>

    <section class="home-page__content-grid">
      <PreferenceRadarChart
        :items="insights"
        title="偏好雷达"
        :loading="loadingInsights"
        :subtitle="insightSummary"
      />

      <aside class="home-page__side-panel">
        <div class="home-page__panel-card">
          <p class="home-page__panel-eyebrow">继续收听</p>
          <template v-if="latestTrack">
            <strong class="home-page__panel-title">{{ latestTrack.name }}</strong>
            <p class="home-page__panel-subtitle">{{ latestTrack.artist }}</p>
            <button class="home-page__panel-button" @click="handlePlay(latestTrack)">
              继续播放
            </button>
          </template>
          <template v-else>
            <strong class="home-page__panel-title">还没有最近播放</strong>
            <p class="home-page__panel-subtitle">听一首歌后，这里会自动帮你接回上次进度。</p>
          </template>
        </div>

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
      empty-text="暂无最近播放记录"
      @play="handlePlay"
    />
  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.25rem 0 0.75rem;
  color: #163025;
}

.home-page__hero {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.95fr);
  gap: 1rem;
  align-items: stretch;
}

.home-page__hero-copy,
.home-page__hero-actions,
.home-page__panel-card {
  border-radius: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 50px rgba(11, 30, 22, 0.08);
}

.home-page__hero-copy {
  padding: 1.35rem 1.4rem;
  background:
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.16), transparent 40%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 252, 248, 0.98));
}

.home-page__eyebrow {
  margin: 0 0 0.4rem;
  font-size: 0.76rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(15, 23, 42, 0.45);
}

.home-page__greeting {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3.35rem);
  line-height: 1.03;
  letter-spacing: -0.04em;
}

.home-page__greeting-mark {
  font-size: 0.84em;
}

.home-page__subtitle {
  margin: 0.85rem 0 0;
  max-width: 48rem;
  color: rgba(15, 23, 42, 0.56);
  font-size: 0.96rem;
}

.home-page__hero-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  padding: 1rem;
}

.home-page__highlight-card {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 1rem;
  border-radius: 20px;
  color: #163025;
  text-align: left;
  border: 1px solid rgba(15, 23, 42, 0.06);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.home-page__highlight-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 30px rgba(11, 30, 22, 0.12);
}

.home-page__highlight-card strong {
  font-size: 1.12rem;
}

.home-page__highlight-card span:last-child {
  color: rgba(15, 23, 42, 0.54);
  font-size: 0.84rem;
  line-height: 1.5;
}

.home-page__highlight-tag,
.home-page__panel-eyebrow {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.home-page__highlight-tag {
  color: rgba(15, 23, 42, 0.44);
}

.home-page__highlight-card--primary {
  background: linear-gradient(180deg, rgba(236, 253, 245, 0.98), rgba(214, 248, 231, 0.9));
}

.home-page__highlight-card--secondary {
  background: linear-gradient(180deg, rgba(255, 250, 235, 0.98), rgba(255, 241, 196, 0.86));
}

.home-page__content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr);
  gap: 1rem;
  align-items: start;
}

.home-page__side-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.home-page__panel-card {
  padding: 1rem;
}

.home-page__panel-card--soft {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(244, 250, 246, 0.96));
}

.home-page__panel-eyebrow {
  margin: 0 0 0.35rem;
  color: rgba(15, 23, 42, 0.42);
}

.home-page__panel-title {
  display: block;
  font-size: 1.05rem;
}

.home-page__panel-subtitle,
.home-page__panel-note {
  margin: 0.35rem 0 0;
  color: rgba(15, 23, 42, 0.55);
  font-size: 0.85rem;
  line-height: 1.55;
}

.home-page__panel-button {
  margin-top: 0.85rem;
  padding: 0.7rem 1rem;
  border-radius: 999px;
  border: none;
  background: linear-gradient(135deg, #0f6b47, #16a34a);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 12px 24px rgba(16, 185, 129, 0.24);
}

.home-page__metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0.4rem 0 0.75rem;
}

.home-page__metrics div {
  padding: 0.85rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.home-page__metrics strong {
  display: block;
  font-size: 1.35rem;
  color: #0f6b47;
}

.home-page__metrics span {
  color: rgba(15, 23, 42, 0.48);
  font-size: 0.78rem;
}

@media (max-width: 1080px) {
  .home-page__hero,
  .home-page__content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .home-page__hero-actions,
  .home-page__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
