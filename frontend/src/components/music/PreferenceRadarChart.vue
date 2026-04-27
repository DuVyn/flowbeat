<script setup lang="ts">
/**
 * PreferenceRadarChart — 偏好雷达图
 *
 * 用 SVG 绘制轻量雷达图，避免引入额外图表依赖。
 */

import { computed } from 'vue'

import type { GenrePreferenceItem } from '@/types/music'

const props = withDefaults(
  defineProps<{
    items: GenrePreferenceItem[]
    title?: string
    subtitle?: string
    loading?: boolean
  }>(),
  {
    title: '偏好雷达图',
    subtitle: '基于最近收听的高频流派生成',
    loading: false,
  },
)

const size = 340
const center = size / 2
const radius = 118
const levels = 5

const points = computed(() => {
  const count = Math.max(props.items.length, 3)
  return props.items.map((item, index) => {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2
    const value = Math.max(0, Math.min(100, item.weight)) / 100
    const r = radius * value
    return {
      x: center + Math.cos(angle) * r,
      y: center + Math.sin(angle) * r,
      labelX: center + Math.cos(angle) * (radius + 28),
      labelY: center + Math.sin(angle) * (radius + 28),
      angle,
      value,
      item,
    }
  })
})

const polygonPath = computed(() => {
  if (points.value.length === 0) {
    return ''
  }
  return points.value
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ')
    .concat(' Z')
})

const concentricLevels = computed(() =>
  Array.from({ length: levels }, (_, levelIndex) => {
    const currentRadius = (radius * (levelIndex + 1)) / levels
    const count = Math.max(props.items.length, 3)
    const levelPoints = Array.from({ length: count }, (_, index) => {
      const angle = (Math.PI * 2 * index) / count - Math.PI / 2
      return {
        x: center + Math.cos(angle) * currentRadius,
        y: center + Math.sin(angle) * currentRadius,
      }
    })
    return levelPoints
  }),
)
</script>

<template>
  <section class="preference-radar">
    <header class="preference-radar__header">
      <div>
        <p class="preference-radar__eyebrow">{{ title }}</p>
        <h2 class="preference-radar__title">理解你的听歌轮廓</h2>
      </div>
      <p class="preference-radar__subtitle">{{ subtitle }}</p>
    </header>

    <div v-if="loading" class="preference-radar__empty">正在生成偏好画像...</div>

    <div v-else-if="items.length === 0" class="preference-radar__empty">暂无足够的收听数据</div>

    <div v-else class="preference-radar__body">
      <svg class="preference-radar__chart" :viewBox="`0 0 ${size} ${size}`" aria-hidden="true">
        <g v-for="(levelPoints, levelIndex) in concentricLevels" :key="levelIndex">
          <polygon
            :points="levelPoints.map((point) => `${point.x},${point.y}`).join(' ')"
            class="preference-radar__grid"
          />
        </g>

        <g v-for="(point, index) in points" :key="point.item.genreCode">
          <line
            :x1="center"
            :y1="center"
            :x2="center + Math.cos(point.angle) * radius"
            :y2="center + Math.sin(point.angle) * radius"
            class="preference-radar__axis"
          />
          <text
            :x="point.labelX"
            :y="point.labelY"
            class="preference-radar__label"
            :class="`preference-radar__label--${index % 5}`"
            text-anchor="middle"
            dominant-baseline="middle"
          >
            {{ point.item.genreName }}
          </text>
        </g>

        <polygon
          v-if="polygonPath"
          :points="points.map((point) => `${point.x},${point.y}`).join(' ')"
          class="preference-radar__shape"
        />

        <circle
          v-for="point in points"
          :key="point.item.genreCode + '-dot'"
          :cx="point.x"
          :cy="point.y"
          r="4.5"
          class="preference-radar__dot"
        />

        <circle :cx="center" :cy="center" r="5" class="preference-radar__center" />
      </svg>

      <div class="preference-radar__legend">
        <div v-for="item in items" :key="item.genreCode" class="preference-radar__legend-item">
          <div>
            <p class="preference-radar__legend-name">{{ item.genreName }}</p>
            <p class="preference-radar__legend-meta">{{ item.playCount }} 次播放</p>
          </div>
          <strong class="preference-radar__legend-weight">{{ item.weight.toFixed(0) }}%</strong>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.preference-radar {
  padding: 1.25rem;
  border-radius: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background:
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.16), transparent 42%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 251, 248, 0.96));
  box-shadow: 0 24px 70px rgba(11, 30, 22, 0.08);
}

.preference-radar__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 1rem;
}

.preference-radar__eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.76rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(15, 23, 42, 0.45);
}

.preference-radar__title {
  margin: 0;
  font-size: 1.15rem;
  letter-spacing: -0.02em;
  color: #163025;
}

.preference-radar__subtitle {
  margin: 0;
  color: rgba(15, 23, 42, 0.48);
  font-size: 0.86rem;
  max-width: 220px;
  text-align: right;
}

.preference-radar__body {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: 1rem;
  align-items: center;
}

.preference-radar__chart {
  width: 100%;
  height: auto;
  overflow: visible;
}

.preference-radar__grid {
  fill: rgba(34, 197, 94, 0.04);
  stroke: rgba(15, 23, 42, 0.08);
  stroke-width: 1;
}

.preference-radar__axis {
  stroke: rgba(15, 23, 42, 0.14);
  stroke-width: 1;
}

.preference-radar__shape {
  fill: rgba(34, 197, 94, 0.28);
  stroke: rgba(22, 163, 74, 0.92);
  stroke-width: 2;
  filter: drop-shadow(0 10px 18px rgba(16, 185, 129, 0.22));
}

.preference-radar__dot {
  fill: #ffffff;
  stroke: #16a34a;
  stroke-width: 2;
}

.preference-radar__center {
  fill: #16a34a;
}

.preference-radar__label {
  font-size: 11px;
  font-weight: 600;
  fill: #163025;
}

.preference-radar__label--1,
.preference-radar__label--3 {
  fill: #0f766e;
}

.preference-radar__legend {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.preference-radar__legend-item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 0.7rem 0.85rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.07);
}

.preference-radar__legend-name {
  margin: 0 0 0.1rem;
  font-weight: 600;
  color: #163025;
}

.preference-radar__legend-meta {
  margin: 0;
  color: rgba(15, 23, 42, 0.48);
  font-size: 0.8rem;
}

.preference-radar__legend-weight {
  font-size: 1.1rem;
  color: #0f6b47;
}

.preference-radar__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  color: rgba(15, 23, 42, 0.45);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px dashed rgba(15, 23, 42, 0.12);
}

@media (max-width: 960px) {
  .preference-radar__header,
  .preference-radar__body {
    grid-template-columns: 1fr;
    display: grid;
  }

  .preference-radar__subtitle {
    text-align: left;
    max-width: none;
  }
}
</style>
