<script setup lang="ts">
/**
 * AuthLayout — 认证页框架布局
 *
 * 左右分栏设计：
 *   - 左侧：品牌展示区（浅绿渐变背景 + SVG 插图 + 品牌文案）
 *   - 右侧：表单内容区（由 <RouterView /> 渲染登录/注册页面）
 *
 * 响应式：移动端隐藏左侧插图区域，仅保留表单。
 */
import loginBgUrl from '@/assets/images/login-register-bg.svg'
</script>

<template>
  <div class="auth-layout">
    <!-- 左侧：品牌展示面板 -->
    <aside class="auth-layout__brand">
      <!-- 渐变装饰圆 -->
      <div class="auth-layout__brand-circle auth-layout__brand-circle--top"></div>
      <div class="auth-layout__brand-circle auth-layout__brand-circle--bottom"></div>

      <!-- 品牌内容 -->
      <div class="auth-layout__brand-content">
        <h1 class="auth-layout__brand-title">FlowBeat</h1>
        <p class="auth-layout__brand-subtitle">让音乐随心而动</p>
        <img
          :src="loginBgUrl"
          alt="FlowBeat 音乐插图"
          class="auth-layout__brand-illustration"
        />
      </div>
    </aside>

    <!-- 右侧：表单区域 -->
    <main class="auth-layout__form-area">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
/* ========================================
 * 设计变量（认证页专用）
 * ======================================== */
.auth-layout {
  /* 主色调：浅绿色系 */
  --auth-primary: #4caf7d;
  --auth-primary-light: #6bcf9a;
  --auth-primary-dark: #3d9e6e;

  /* 背景色 */
  --auth-bg-brand: #e8f5ee;
  --auth-bg-form: #f5faf7;

  /* 文字色 */
  --auth-text-primary: #1a2e1a;
  --auth-text-secondary: rgba(26, 46, 26, 0.6);

  display: flex;
  min-height: 100vh;
  background-color: var(--auth-bg-form);
}

/* ========================================
 * 左侧：品牌展示面板
 * ======================================== */
.auth-layout__brand {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;

  /* 浅绿色渐变背景 */
  background: linear-gradient(
    135deg,
    var(--auth-bg-brand) 0%,
    #d4edda 50%,
    var(--auth-bg-brand) 100%
  );
}

/* 装饰性渐变圆 —— 增加视觉层次 */
.auth-layout__brand-circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.18;
  pointer-events: none;
}

.auth-layout__brand-circle--top {
  width: 500px;
  height: 500px;
  top: -160px;
  left: -100px;
  background: radial-gradient(circle, var(--auth-primary) 0%, transparent 70%);
}

.auth-layout__brand-circle--bottom {
  width: 400px;
  height: 400px;
  bottom: -120px;
  right: -80px;
  background: radial-gradient(circle, #81c784 0%, transparent 70%);
}

/* 品牌内容容器 */
.auth-layout__brand-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  text-align: center;
}

/* 品牌标题 */
.auth-layout__brand-title {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  font-size: 2.75rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--auth-text-primary);
  margin: 0 0 0.5rem;

  /* 渐变文字效果 */
  background: linear-gradient(135deg, #1a2e1a 30%, var(--auth-primary));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 品牌副标题 */
.auth-layout__brand-subtitle {
  font-size: 1.125rem;
  color: var(--auth-text-secondary);
  margin: 0 0 3rem;
  letter-spacing: 0.15em;
}

/* SVG 插图 */
.auth-layout__brand-illustration {
  width: min(80%, 420px);
  height: auto;
  filter: drop-shadow(0 20px 40px rgba(76, 175, 125, 0.15));
  animation: auth-float 6s ease-in-out infinite;
}

/* 插图悬浮动画 */
@keyframes auth-float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-16px); }
}

/* ========================================
 * 右侧：表单区域
 * ======================================== */
.auth-layout__form-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

/* ========================================
 * 响应式：移动端（< 768px）
 * ======================================== */
@media (max-width: 768px) {
  .auth-layout {
    flex-direction: column;
  }

  /* 移动端隐藏左侧品牌区域 */
  .auth-layout__brand {
    display: none;
  }

  .auth-layout__form-area {
    flex: 1;
    padding: 1.5rem;
  }
}
</style>
