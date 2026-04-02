<script setup lang="ts">
/**
 * HomePage — 首页/推荐页
 *
 * 展示推荐音乐列表，当前使用 Mock 数据（20 首周杰伦《晴天》）。
 */

import { ref } from 'vue'
import type { Track } from '@/types/music'
import MusicList from '@/components/music/MusicList.vue'
import mockCover from '@/assets/images/mock-cover-sunny.png'

/* ========================================
 * Mock 数据：生成 20 首《晴天》
 * ======================================== */
function generateMockTracks(count: number): Track[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `track-sunny-${i + 1}`,
    name: '晴天',
    artist: '周杰伦',
    album: '叶惠美',
    coverUrl: mockCover,
    durationMs: 269000, // 4:29
  }))
}

const tracks = ref<Track[]>(generateMockTracks(20))

function handlePlay(track: Track) {
  console.log('▶ 播放:', track.name, '-', track.artist)
}
</script>

<template>
  <div class="home-page">
    <!-- 页面头部 -->
    <header class="home-page__hero">
      <h1 class="home-page__greeting">下午好 🎵</h1>
      <p class="home-page__subtitle">为你推荐今日精选音乐</p>
    </header>

    <!-- 推荐歌曲列表 -->
    <MusicList
      title="今日推荐"
      :tracks="tracks"
      @play="handlePlay"
    />
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
</style>
