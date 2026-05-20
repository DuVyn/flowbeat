<script setup lang="ts">
/**
 * DiscoverPage — 发现音乐页
 *
 * 拆分为排行榜、新歌速递和流派导航三大模块。
 */

import { computed, onMounted, ref } from 'vue'

import { getGenreCatalog, getGenreSongs } from '@/api/genres'
import { getHotRecommendations } from '@/api/recommendation'
import { getLatestSongs } from '@/api/song'
import defaultCover from '@/assets/images/default-cover.svg'
import MusicList from '@/components/music/MusicList.vue'
import { usePlayerStore } from '@/stores/player'
import { useCoverStore } from '@/stores/cover'
import type { GenreCatalogItem, Track } from '@/types/music'

const playerStore = usePlayerStore()
const coverStore = useCoverStore()

const hotTracks = ref<Track[]>([])
const latestTracks = ref<Track[]>([])
const genreTracks = ref<Track[]>([])
const genreCatalog = ref<GenreCatalogItem[]>([])
const activeGenreCode = ref('')

const hotLoading = ref(true)
const latestLoading = ref(true)
const genreLoading = ref(true)
const catalogLoading = ref(true)
const hotLoadingMore = ref(false)
const latestLoadingMore = ref(false)
const genreLoadingMore = ref(false)
const hotHasMore = ref(false)
const latestHasMore = ref(false)
const genreHasMore = ref(false)

const hotError = ref('')
const latestError = ref('')
const genreError = ref('')

const activeGenre = computed(
  () => genreCatalog.value.find((item) => item.genreCode === activeGenreCode.value) ?? null,
)

const topThreeTracks = computed(() => hotTracks.value.slice(0, 3))

function scrollTo(sectionId: string): void {
  document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function coverUrl(track: Track): string {
  const cached = coverStore.getCoverUrl(track.id)
  if (cached) return cached
  return track.coverUrl?.trim() || defaultCover
}

async function loadHotRecommendations(): Promise<void> {
  hotLoading.value = true
  hotError.value = ''
  try {
    const response = await getHotRecommendations(20, 0)
    hotTracks.value = response.items
    hotHasMore.value = response.items.length >= 20 || response.total > response.items.length
  } catch (error) {
    hotError.value = error instanceof Error ? error.message : '今日推荐加载失败，请稍后重试'
    hotTracks.value = []
  } finally {
    hotLoading.value = false
  }
}

async function loadMoreHotRecommendations(): Promise<void> {
  if (hotLoading.value || hotLoadingMore.value || !hotHasMore.value) {
    return
  }

  hotLoadingMore.value = true
  hotError.value = ''
  try {
    const response = await getHotRecommendations(20, hotTracks.value.length)
    hotTracks.value = [...hotTracks.value, ...response.items]
    hotHasMore.value = response.items.length >= 20 || response.total > hotTracks.value.length
  } catch (error) {
    hotError.value = error instanceof Error ? error.message : '今日推荐加载失败，请稍后重试'
  } finally {
    hotLoadingMore.value = false
  }
}

async function loadLatestSongs(): Promise<void> {
  latestLoading.value = true
  latestError.value = ''
  try {
    const response = await getLatestSongs(10, 0)
    latestTracks.value = response.items
    latestHasMore.value = response.items.length >= 10 || response.hasMore
  } catch (error) {
    latestError.value = error instanceof Error ? error.message : '新歌速递加载失败，请稍后重试'
    latestTracks.value = []
  } finally {
    latestLoading.value = false
  }
}

async function loadMoreLatestSongs(): Promise<void> {
  if (latestLoading.value || latestLoadingMore.value || !latestHasMore.value) {
    return
  }

  latestLoadingMore.value = true
  latestError.value = ''
  try {
    const response = await getLatestSongs(10, latestTracks.value.length)
    latestTracks.value = [...latestTracks.value, ...response.items]
    latestHasMore.value = response.items.length >= 10 || response.hasMore
  } catch (error) {
    latestError.value = error instanceof Error ? error.message : '新歌速递加载失败，请稍后重试'
  } finally {
    latestLoadingMore.value = false
  }
}

async function loadGenreCatalog(): Promise<void> {
  catalogLoading.value = true
  genreError.value = ''
  try {
    const response = await getGenreCatalog()
    genreCatalog.value = response.items
    activeGenreCode.value = response.items[0]?.genreCode ?? ''
    if (activeGenreCode.value) {
      await loadGenreSongs(activeGenreCode.value)
    }
  } catch (error) {
    genreError.value = error instanceof Error ? error.message : '流派目录加载失败，请稍后重试'
    genreCatalog.value = []
    activeGenreCode.value = ''
  } finally {
    catalogLoading.value = false
  }
}

async function loadGenreSongs(genreCode: string): Promise<void> {
  if (!genreCode) {
    genreTracks.value = []
    genreHasMore.value = false
    return
  }

  genreLoading.value = true
  genreError.value = ''
  try {
    const response = await getGenreSongs(genreCode, 12, 0)
    genreTracks.value = response.items
    genreHasMore.value = response.items.length >= 12 || response.hasMore
  } catch (error) {
    genreError.value = error instanceof Error ? error.message : '流派歌曲加载失败，请稍后重试'
    genreTracks.value = []
    genreHasMore.value = false
  } finally {
    genreLoading.value = false
  }
}

async function loadMoreGenreSongs(): Promise<void> {
  if (
    genreLoading.value ||
    genreLoadingMore.value ||
    !genreHasMore.value ||
    !activeGenreCode.value
  ) {
    return
  }

  genreLoadingMore.value = true
  genreError.value = ''
  try {
    const response = await getGenreSongs(activeGenreCode.value, 12, genreTracks.value.length)
    genreTracks.value = [...genreTracks.value, ...response.items]
    genreHasMore.value = response.items.length >= 12 || response.hasMore
  } catch (error) {
    genreError.value = error instanceof Error ? error.message : '流派歌曲加载失败，请稍后重试'
  } finally {
    genreLoadingMore.value = false
  }
}

function handleGenreSelect(genreCode: string): void {
  activeGenreCode.value = genreCode
  void loadGenreSongs(genreCode)
}

function handlePlay(track: Track, playlist: Track[] = hotTracks.value): void {
  void playerStore.playTrack(track, playlist)
}

onMounted(() => {
  void loadHotRecommendations()
  void loadLatestSongs()
  void loadGenreCatalog()
})
</script>

<template>
  <div class="discover-page">
    <header class="discover-page__hero">
      <div>
        <p class="discover-page__eyebrow">发现音乐</p>
        <h1 class="discover-page__title">今日推荐</h1>
        <p class="discover-page__subtitle">热门、新歌与流派入口一次看完，快速开启探索。</p>
      </div>
      <button class="discover-page__jump" @click="scrollTo('discover-genre-section')">
        流派导航
      </button>
    </header>

    <section class="discover-page__module" id="discover-hot-list">
      <div class="discover-page__module-head">
        <div>
          <p class="discover-page__module-eyebrow">排行榜</p>
          <h2 class="discover-page__module-title">今日推荐 Top 3</h2>
          <p class="discover-page__module-subtitle">精简卡片展示前三首，点击即可播放。</p>
        </div>
        <button class="discover-page__jump-link" @click="scrollTo('discover-hot-full')">
          查看完整榜单
        </button>
      </div>

      <div v-if="hotError" class="discover-page__error">{{ hotError }}</div>

      <div class="discover-page__top-three">
        <button
          v-for="(track, index) in topThreeTracks"
          :key="track.id"
          class="discover-page__rank-card"
          @click="handlePlay(track)"
        >
          <div class="discover-page__rank-index">#{{ index + 1 }}</div>
          <div class="discover-page__rank-cover-wrap">
            <img
              class="discover-page__rank-cover"
              :src="coverUrl(track)"
              :alt="`${track.name} 封面`"
              loading="lazy"
            />
          </div>
          <div class="discover-page__rank-meta">
            <strong>{{ track.name }}</strong>
            <span>{{ track.artist }}</span>
          </div>
        </button>
      </div>

      <MusicList
        id="discover-hot-full"
        title="今日推荐完整榜单"
        :tracks="hotTracks"
        :loading="hotLoading"
        :has-more="hotHasMore"
        :loading-more="hotLoadingMore"
        @play="handlePlay"
        @load-more="loadMoreHotRecommendations"
      />
    </section>

    <section class="discover-page__module">
      <div class="discover-page__module-head">
        <div>
          <p class="discover-page__module-eyebrow">新歌速递</p>
          <h2 class="discover-page__module-title">最新上架</h2>
          <p class="discover-page__module-subtitle">最新入库的单曲，适合随手刷新。</p>
        </div>
      </div>

      <div v-if="latestError" class="discover-page__error">{{ latestError }}</div>

      <MusicList
        title="新歌速递"
        :tracks="latestTracks"
        :loading="latestLoading"
        :has-more="latestHasMore"
        :loading-more="latestLoadingMore"
        @play="(track) => handlePlay(track, latestTracks)"
        @load-more="loadMoreLatestSongs"
      />
    </section>

    <section class="discover-page__module" id="discover-genre-section">
      <div class="discover-page__module-head">
        <div>
          <p class="discover-page__module-eyebrow">流派导航</p>
          <h2 class="discover-page__module-title">按流派继续探索</h2>
          <p class="discover-page__module-subtitle">点击标签筛选对应流派的歌曲。</p>
        </div>
        <span
          v-if="activeGenre"
          class="discover-page__genre-chip discover-page__genre-chip--active"
        >
          {{ activeGenre.genreName }} · {{ activeGenre.songCount }} 首
        </span>
      </div>

      <div v-if="genreError" class="discover-page__error">{{ genreError }}</div>

      <div class="discover-page__genre-cloud">
        <button
          v-for="genre in genreCatalog"
          :key="genre.genreCode"
          class="discover-page__genre-chip"
          :class="{ 'discover-page__genre-chip--active': genre.genreCode === activeGenreCode }"
          @click="handleGenreSelect(genre.genreCode)"
        >
          {{ genre.genreName }}
          <span>{{ genre.songCount }}</span>
        </button>
      </div>

      <MusicList
        :title="activeGenre?.genreName || '流派歌曲'"
        :tracks="genreTracks"
        :loading="genreLoading || catalogLoading"
        :has-more="genreHasMore"
        :loading-more="genreLoadingMore"
        @play="(track) => handlePlay(track, genreTracks)"
        @load-more="loadMoreGenreSongs"
      />
    </section>
  </div>
</template>

<style scoped>
.discover-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.5rem 0 1rem;
  color: var(--ink-900);
}

.discover-page__hero,
.discover-page__module {
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
}

.discover-page__hero {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.1rem;
  align-items: flex-end;
}

.discover-page__eyebrow,
.discover-page__module-eyebrow {
  margin: 0 0 0.5rem;
  font-size: 0.76rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-300);
}

.discover-page__title,
.discover-page__module-title {
  margin: 0;
  line-height: 1.1;
}

.discover-page__title {
  font-size: clamp(1.7rem, 3.6vw, 2.3rem);
  letter-spacing: -0.03em;
}

.discover-page__subtitle,
.discover-page__module-subtitle {
  margin: 0.5rem 0 0;
  color: var(--ink-500);
  font-size: 0.92rem;
  max-width: 54rem;
}

.discover-page__jump,
.discover-page__jump-link {
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

.discover-page__jump:hover,
.discover-page__jump-link:hover {
  background: #ffffff;
  box-shadow: var(--shadow-soft);
  transform: translateY(-1px);
}

.discover-page__module {
  padding: 1rem;
}

.discover-page__module-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 0.5rem;
}

.discover-page__top-three {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
  padding: 0.5rem 0;
  margin-bottom: 0.5rem;
}

.discover-page__rank-card {
  display: grid;
  grid-template-columns: 120px 1fr;
  grid-template-areas:
    'cover index'
    'cover meta';
  gap: 0.5rem;
  align-items: center;
  padding: 1rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.discover-page__rank-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-strong);
}

.discover-page__rank-index {
  grid-area: index;
  width: fit-content;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: var(--surface-1);
  color: var(--ink-700);
  font-weight: 700;
  font-size: 0.74rem;
}

.discover-page__rank-cover-wrap {
  grid-area: cover;
  overflow: hidden;
  border-radius: 12px;
  width: 120px;
  height: 120px;
}

.discover-page__rank-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.discover-page__rank-meta {
  grid-area: meta;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.discover-page__rank-meta strong {
  font-size: 0.95rem;
  color: var(--ink-900);
}

.discover-page__rank-meta span {
  color: var(--ink-500);
  font-size: 0.82rem;
}

.discover-page__genre-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.discover-page__genre-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  color: var(--ink-700);
}

.discover-page__genre-chip span {
  color: var(--ink-300);
  font-size: 0.78rem;
}

.discover-page__genre-chip--active {
  background: var(--accent-600);
  color: #fff;
  border-color: var(--accent-600);
}

.discover-page__genre-chip--active span {
  color: rgba(255, 255, 255, 0.8);
}

.discover-page__error {
  margin-bottom: 0.9rem;
  padding: 0.75rem 0.9rem;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(181, 63, 75, 0.2);
  color: #9b2f3a;
  background: rgba(255, 235, 238, 0.7);
}

.discover-page__module-head :deep(.discover-page__jump-link) {
  white-space: nowrap;
}

@media (max-width: 960px) {
  .discover-page__hero,
  .discover-page__module-head,
  .discover-page__top-three {
    grid-template-columns: 1fr;
    display: grid;
  }

  .discover-page__hero {
    display: grid;
  }

  .discover-page__module-head {
    display: grid;
  }

  .discover-page__top-three {
    grid-template-columns: 1fr;
  }

  .discover-page__rank-card {
    grid-template-columns: 96px 1fr;
  }

  .discover-page__rank-cover-wrap {
    width: 96px;
    height: 96px;
  }
}
</style>
