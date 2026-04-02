<script setup lang="ts">
/**
 * App.vue — 根组件
 *
 * 仅承载 <RouterView />，不包含任何业务逻辑与布局样式。
 * 所有页面布局由 layouts/ 下的布局组件负责。
 */
</script>

<template>
  <!--
    根组件唯一职责：渲染当前路由匹配的组件。
    布局切换通过路由嵌套（DefaultLayout / AuthLayout）实现。
  -->
  <RouterView />
</template>
