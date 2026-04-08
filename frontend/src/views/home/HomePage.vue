<script setup lang="ts">
/**
 * HomePage — 首页/推荐页
 *
 * 展示后端返回的全局热门推荐列表。
 */

import { onMounted, ref } from 'vue'
import type { Track } from '@/types/music'
import MusicList from '@/components/music/MusicList.vue'
import { getHotRecommendations } from '@/api/recommendation'
import { usePlayerStore } from '@/stores/player'

const playerStore = usePlayerStore()

const tracks = ref<Track[]>([])
const loading = ref(true)
const loadError = ref('')

async function loadHotRecommendations() {
  loading.value = true
  loadError.value = ''

  try {
    const response = await getHotRecommendations(20, 0)
    tracks.value = response.items
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '推荐加载失败，请稍后重试'
    tracks.value = []
  } finally {
    loading.value = false
  }
}

function handlePlay(track: Track) {
  void playerStore.playTrack(track, tracks.value)
}

onMounted(() => {
  void loadHotRecommendations()
})
</script>

<template>
  <div class="home-page">
    <!-- 页面头部 -->
    <header class="home-page__hero">
      <h1 class="home-page__greeting">下午好 🎵</h1>
      <p class="home-page__subtitle">为你推荐全站热门歌曲</p>
    </header>

    <div v-if="loadError" class="home-page__error">
      <span>{{ loadError }}</span>
      <button class="home-page__retry" @click="loadHotRecommendations">重试</button>
    </div>

    <!-- 推荐歌曲列表 -->
    <MusicList title="今日推荐" :tracks="tracks" :loading="loading" @play="handlePlay" />
  </div>
</template>

<style scoped>
.home-page {
  padding: 0.5rem 0;
  color: #1a2e1a;
}

/* ---- 顶部欢迎区域 ---- */
.home-page__hero {
  margin-bottom: 2rem;
}

.home-page__greeting {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #2e7d32, #66bb6a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.home-page__subtitle {
  color: rgba(0, 0, 0, 0.45);
  margin: 0;
  font-size: 0.9rem;
}

.home-page__error {
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

.home-page__retry {
  border: none;
  border-radius: 6px;
  padding: 0.35rem 0.75rem;
  background: #1a2e1a;
  color: #fff;
  cursor: pointer;
  font-size: 0.78rem;
}
</style>
