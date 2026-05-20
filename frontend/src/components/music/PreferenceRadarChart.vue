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

const size = 280
const center = size / 2
const radius = 92
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
      labelX: center + Math.cos(angle) * (radius + 22),
      labelY: center + Math.sin(angle) * (radius + 22),
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
      <div style="width: 100%">
        <p class="preference-radar__eyebrow">{{ title }}</p>
        <div class="preference-radar__title-row">
          <h2 class="preference-radar__title">理解你的听歌轮廓</h2>
          <p class="preference-radar__subtitle">{{ subtitle }}</p>
        </div>
      </div>
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
  padding: 1rem;
  border-radius: var(--radius-xl);
  border: 1px solid var(--surface-border);
  background: var(--surface-0);
  box-shadow: var(--shadow-soft);
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
  font-size: 1.12rem;
  font-weight: 700;
  color: var(--ink-900);
}

.preference-radar__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 400;
  line-height: 1.55;
  color: var(--ink-500);
}

.preference-radar__subtitle {
  margin: 0;
  color: var(--ink-500);
  font-size: 0.95rem;
  font-weight: 400;
  line-height: 1.55;
  max-width: none;
  text-align: right;
}

.preference-radar__title-row {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.preference-radar__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.8fr);
  gap: 1rem;
  align-items: center;
}

.preference-radar__chart {
  width: 100%;
  height: auto;
  overflow: visible;
}

.preference-radar__grid {
  fill: rgba(15, 23, 42, 0.03);
  stroke: rgba(15, 23, 42, 0.12);
  stroke-width: 1;
}

.preference-radar__axis {
  stroke: rgba(15, 23, 42, 0.16);
  stroke-width: 1;
}

.preference-radar__shape {
  fill: rgba(20, 91, 67, 0.18);
  stroke: var(--accent-600);
  stroke-width: 2;
  filter: drop-shadow(0 10px 18px rgba(15, 23, 42, 0.18));
}

.preference-radar__dot {
  fill: #ffffff;
  stroke: var(--accent-600);
  stroke-width: 2;
}

.preference-radar__center {
  fill: var(--accent-600);
}

.preference-radar__label {
  font-size: 11px;
  font-weight: 600;
  fill: var(--ink-700);
}

.preference-radar__label--1,
.preference-radar__label--3 {
  fill: var(--accent-600);
}

.preference-radar__legend {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.preference-radar__legend-item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-lg);
  background: var(--surface-1);
  border: 1px solid var(--surface-border);
}

.preference-radar__legend-name {
  margin: 0 0 0.1rem;
  font-weight: 600;
  color: var(--ink-900);
}

.preference-radar__legend-meta {
  margin: 0;
  color: var(--ink-500);
  font-size: 0.8rem;
}

.preference-radar__legend-weight {
  font-size: 1.1rem;
  color: var(--accent-600);
}

.preference-radar__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  color: var(--ink-500);
  border-radius: var(--radius-lg);
  background: var(--surface-1);
  border: 1px dashed var(--surface-border);
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
    white-space: normal;
  }

  .preference-radar__title-row {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    align-items: flex-start;
  }
}
</style>
