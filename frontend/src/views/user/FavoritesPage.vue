<script setup lang="ts">
/**
 * FavoritesPage — 我喜欢页面
 *
 * 使用虚拟列表展示当前用户收藏的歌曲，支持分页追加与行内取消收藏。
 */

import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { HttpError } from '@/api/http'
import { getFavoriteSongs, toggleFavorite } from '@/api/favorites'
import MusicList from '@/components/music/MusicList.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import type { FavoriteTrackItem } from '@/types/music'

const PAGE_SIZE = 20

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const playerStore = usePlayerStore()

const tracks = ref<FavoriteTrackItem[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(false)
const loadError = ref('')
const toggleBusyIds = ref<Set<number>>(new Set())

async function loadFavorites(reset = false): Promise<void> {
  if (reset) {
    loading.value = true
    loadError.value = ''
  } else {
    if (loading.value || loadingMore.value || !hasMore.value) {
      return
    }
    loadingMore.value = true
  }

  try {
    const offset = reset ? 0 : tracks.value.length
    const response = await getFavoriteSongs(PAGE_SIZE, offset)
    hasMore.value = response.hasMore
    tracks.value = reset ? response.items : [...tracks.value, ...response.items]
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      authStore.clearSession()
      await router.replace({
        name: 'Login',
        query: { redirect: route.fullPath },
      })
      return
    }

    loadError.value = error instanceof Error ? error.message : '收藏列表加载失败，请稍后重试'
    if (reset) {
      tracks.value = []
      hasMore.value = false
    }
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

function handlePlay(track: FavoriteTrackItem): void {
  void playerStore.playTrack(track, tracks.value)
}

async function handleToggleFavorite(track: FavoriteTrackItem): Promise<void> {
  if (toggleBusyIds.value.has(track.id)) {
    return
  }

  const previousLikedState = track.isLiked
  toggleBusyIds.value = new Set(toggleBusyIds.value).add(track.id)
  track.isLiked = !previousLikedState

  try {
    const response = await toggleFavorite(track.id)
    if (!response.isLiked) {
      tracks.value = tracks.value.filter((item) => item.id !== track.id)
    } else {
      track.isLiked = true
    }
  } catch (error) {
    track.isLiked = previousLikedState
    loadError.value = error instanceof Error ? error.message : '取消收藏失败，请稍后重试'
  } finally {
    const nextBusyIds = new Set(toggleBusyIds.value)
    nextBusyIds.delete(track.id)
    toggleBusyIds.value = nextBusyIds
  }
}

function loadMoreFavorites(): void {
  void loadFavorites(false)
}

function refreshFavorites(): void {
  void loadFavorites(true)
}

onMounted(() => {
  void loadFavorites(true)
})
</script>

<template>
  <div class="favorites-page">
    <header class="favorites-page__hero">
      <div>
        <p class="favorites-page__eyebrow">我的音乐</p>
        <h1 class="favorites-page__title">我喜欢</h1>
        <p class="favorites-page__subtitle">
          把收藏过的歌曲集中在一起，支持继续播放，也能直接取消收藏。
        </p>
      </div>

      <button
        class="favorites-page__refresh"
        :disabled="loading || loadingMore"
        @click="refreshFavorites"
      >
        {{ loading || loadingMore ? '刷新中...' : '刷新列表' }}
      </button>
    </header>

    <section class="favorites-page__stats">
      <div class="favorites-page__stat-card">
        <span>收藏总数</span>
        <strong>{{ tracks.length }}</strong>
      </div>
      <div class="favorites-page__stat-card favorites-page__stat-card--soft">
        <span>加载状态</span>
        <strong>{{ loading ? '首屏加载中' : loadingMore ? '继续加载中' : '就绪' }}</strong>
      </div>
    </section>

    <div v-if="loadError" class="favorites-page__error">
      <span>{{ loadError }}</span>
      <button
        class="favorites-page__retry"
        :disabled="loading || loadingMore"
        @click="refreshFavorites"
      >
        {{ loading ? '重试中...' : '重试' }}
      </button>
    </div>

    <MusicList
      title="收藏列表"
      :tracks="tracks"
      :loading="loading"
      :has-more="hasMore"
      :loading-more="loadingMore"
      :show-like-action="true"
      @play="handlePlay"
      @load-more="loadMoreFavorites"
      @toggle-like="handleToggleFavorite"
    />

    <p v-if="!loading && !loadError && tracks.length === 0" class="favorites-page__empty">
      还没有收藏任何歌曲，去发现页或搜索页点亮几首喜欢的音乐吧。
    </p>
  </div>
</template>

<style scoped>
.favorites-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0 0.75rem;
  color: #163025;
}

.favorites-page__hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.favorites-page__eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.76rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(15, 23, 42, 0.45);
}

.favorites-page__title {
  margin: 0;
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  letter-spacing: -0.04em;
  line-height: 1.08;
}

.favorites-page__subtitle {
  margin: 0.7rem 0 0;
  color: rgba(15, 23, 42, 0.56);
  font-size: 0.94rem;
  max-width: 54rem;
}

.favorites-page__refresh {
  border: none;
  border-radius: 999px;
  padding: 0.7rem 1rem;
  background: linear-gradient(135deg, #b91c1c, #ef4444);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 12px 24px rgba(239, 68, 68, 0.22);
}

.favorites-page__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.favorites-page__stat-card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 1rem 1.1rem;
  border-radius: 20px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 12px 32px rgba(11, 30, 22, 0.06);
}

.favorites-page__stat-card--soft {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(244, 114, 182, 0.08));
}

.favorites-page__stat-card span {
  font-size: 0.8rem;
  color: rgba(15, 23, 42, 0.48);
}

.favorites-page__stat-card strong {
  font-size: 1.4rem;
  letter-spacing: -0.03em;
}

.favorites-page__error {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.8rem 1rem;
  border-radius: 16px;
  border: 1px solid rgba(220, 38, 38, 0.22);
  background: rgba(254, 242, 242, 0.92);
  color: #991b1b;
}

.favorites-page__retry {
  border: none;
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  background: #b91c1c;
  color: #fff;
}

.favorites-page__empty {
  margin: 0;
  padding: 1rem 1.1rem;
  border-radius: 18px;
  border: 1px dashed rgba(15, 23, 42, 0.14);
  color: rgba(15, 23, 42, 0.56);
  background: rgba(255, 255, 255, 0.72);
}

@media (max-width: 720px) {
  .favorites-page__hero,
  .favorites-page__stats,
  .favorites-page__error {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
