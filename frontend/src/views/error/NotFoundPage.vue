<script setup lang="ts">
/**
 * NotFoundPage — 404 页面
 *
 * 当用户访问不存在的路由时展示此页面。
 */
</script>

<template>
  <div class="not-found-page">
    <h1>404</h1>
    <p>页面未找到</p>
    <router-link to="/" class="not-found-page__link">返回首页</router-link>
  </div>
</template>

<style scoped>
.not-found-page {
  text-align: center;
  padding: 4rem 2rem;
  color: #1a2e1a;
}

.not-found-page h1 {
  font-size: 4rem;
  font-weight: 800;
  color: rgba(0, 0, 0, 0.15);
  margin: 0 0 0.5rem;
}

.not-found-page p {
  color: rgba(0, 0, 0, 0.5);
  margin: 0 0 1.5rem;
}

.not-found-page__link {
  color: #4caf7d;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s ease;
}

.not-found-page__link:hover {
  color: #3d9e6e;
}
</style>
