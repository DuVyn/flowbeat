<script setup lang="ts">
/**
 * LoginPage — 登录 / 注册页面
 *
 * 功能：
 *   1. 「登录」与「注册」选项卡切换
 *   2. 登录表单：邮箱 + 密码
 *   3. 注册表单：用户名 + 性别 + 生日（全下拉）+ 邮箱 + 密码
 *   4. 与后端 Auth API 联调
 *
 * 与 AuthLayout 配合：本组件渲染在右侧表单区域内。
 */

import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import { HttpError } from '@/api/http'
import { login, register } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { GenderValue } from '@/types/auth'

/* ---- 选项卡 ---- */
type AuthTab = 'login' | 'register'
const activeTab = ref<AuthTab>('login')

/* ---- 路由实例（提交后跳转用） ---- */
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

/* ---- 登录表单 ---- */
const loginForm = reactive({
  email: '',
  password: '',
})

/* ---- 注册表单 ---- */
const registerForm = reactive({
  username: '',
  gender: 'unknown' as GenderValue,
  birthYear: '',
  birthMonth: '',
  birthDay: '',
  email: '',
  password: '',
  confirmPassword: '',
})

/* ---- 通用状态 ---- */
const isSubmitting = ref(false)
const errorMessage = ref('')

/* ---- 密码可见性切换 ---- */
const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)
const showRegisterConfirm = ref(false)

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 100 }, (_, index) => String(currentYear - index))
const monthOptions = Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, '0'))

const dayOptions = computed(() => {
  const year = Number(registerForm.birthYear || currentYear)
  const month = Number(registerForm.birthMonth || 1)
  const daysInMonth = new Date(year, month, 0).getDate()
  return Array.from({ length: daysInMonth }, (_, index) => String(index + 1).padStart(2, '0'))
})

const birthday = computed(() => {
  if (!registerForm.birthYear || !registerForm.birthMonth || !registerForm.birthDay) {
    return null
  }
  return `${registerForm.birthYear}-${registerForm.birthMonth}-${registerForm.birthDay}`
})

/* ---- 注册表单：密码匹配校验 ---- */
const passwordMismatch = computed(() => {
  return (
    registerForm.confirmPassword.length > 0 &&
    registerForm.password !== registerForm.confirmPassword
  )
})

/* ---- 切换选项卡 ---- */
function switchTab(tab: AuthTab) {
  activeTab.value = tab
  errorMessage.value = ''
}

async function handleLogin() {
  errorMessage.value = ''

  if (!loginForm.email.trim()) {
    errorMessage.value = '请输入邮箱'
    return
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(loginForm.email)) {
    errorMessage.value = '邮箱格式不正确'
    return
  }

  if (!loginForm.password) {
    errorMessage.value = '请输入密码'
    return
  }

  isSubmitting.value = true
  try {
    const response = await login({
      email: loginForm.email.trim(),
      password: loginForm.password,
    })
    authStore.setAuthSession(response)

    const redirect = (route.query.redirect as string) || '/'
    await router.replace(redirect)
  } catch (error) {
    if (error instanceof HttpError) {
      errorMessage.value = error.detail
    } else {
      errorMessage.value = '登录失败，请稍后重试'
    }
  } finally {
    isSubmitting.value = false
  }
}

async function handleRegister() {
  errorMessage.value = ''

  if (!registerForm.username.trim()) {
    errorMessage.value = '请输入用户名'
    return
  }

  if (!registerForm.gender) {
    errorMessage.value = '请选择性别'
    return
  }

  if (!birthday.value) {
    errorMessage.value = '请选择完整生日'
    return
  }
  const birthdayValue = birthday.value

  if (!registerForm.email.trim()) {
    errorMessage.value = '请输入邮箱'
    return
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(registerForm.email)) {
    errorMessage.value = '邮箱格式不正确'
    return
  }
  if (registerForm.password.length < 6) {
    errorMessage.value = '密码长度至少 6 位'
    return
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  isSubmitting.value = true
  try {
    const response = await register({
      username: registerForm.username.trim(),
      gender: registerForm.gender,
      birthday: birthdayValue,
      email: registerForm.email.trim(),
      password: registerForm.password,
    })
    authStore.setAuthSession(response)

    const redirect = (route.query.redirect as string) || '/'
    await router.replace(redirect)
  } catch (error) {
    if (error instanceof HttpError) {
      errorMessage.value = error.detail
    } else {
      errorMessage.value = '注册失败，请稍后重试'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="auth-card">
    <!-- 选项卡栏 -->
    <div class="auth-card__tabs">
      <button
        class="auth-card__tab"
        :class="{ 'auth-card__tab--active': activeTab === 'login' }"
        @click="switchTab('login')"
      >
        登录
      </button>
      <button
        class="auth-card__tab"
        :class="{ 'auth-card__tab--active': activeTab === 'register' }"
        @click="switchTab('register')"
      >
        注册
      </button>
      <!-- 选项卡底部指示条 -->
      <div
        class="auth-card__tab-indicator"
        :class="{ 'auth-card__tab-indicator--right': activeTab === 'register' }"
      ></div>
    </div>

    <!-- 错误提示 -->
    <Transition name="auth-fade">
      <div v-if="errorMessage" class="auth-card__error">
        <span class="auth-card__error-icon">⚠</span>
        {{ errorMessage }}
      </div>
    </Transition>

    <!-- ==================== 登录表单 ==================== -->
    <Transition name="auth-slide" mode="out-in">
      <form
        v-if="activeTab === 'login'"
        key="login"
        class="auth-card__form"
        @submit.prevent="handleLogin"
      >
        <!-- 邮箱 -->
        <div class="auth-card__field">
          <label class="auth-card__label" for="login-email">邮箱</label>
          <div class="auth-card__input-wrapper">
            <svg
              class="auth-card__input-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
              />
              <polyline points="22,6 12,13 2,6" />
            </svg>
            <input
              id="login-email"
              v-model="loginForm.email"
              type="email"
              class="auth-card__input"
              placeholder="请输入邮箱"
              autocomplete="email"
            />
          </div>
        </div>

        <!-- 密码 -->
        <div class="auth-card__field">
          <label class="auth-card__label" for="login-password">密码</label>
          <div class="auth-card__input-wrapper">
            <svg
              class="auth-card__input-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <input
              id="login-password"
              v-model="loginForm.password"
              :type="showLoginPassword ? 'text' : 'password'"
              class="auth-card__input"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
            <!-- 密码可见切换按钮 -->
            <button
              type="button"
              class="auth-card__input-toggle"
              @click="showLoginPassword = !showLoginPassword"
              :aria-label="showLoginPassword ? '隐藏密码' : '显示密码'"
            >
              <!-- 眼睛图标 -->
              <svg
                v-if="!showLoginPassword"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              <!-- 闭眼图标 -->
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path
                  d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 提交按钮 -->
        <button type="submit" class="auth-card__submit" :disabled="isSubmitting">
          <span v-if="isSubmitting" class="auth-card__spinner"></span>
          <span v-else>登 录</span>
        </button>
      </form>

      <!-- ==================== 注册表单 ==================== -->
      <form v-else key="register" class="auth-card__form" @submit.prevent="handleRegister">
        <!-- 用户名 -->
        <div class="auth-card__field">
          <label class="auth-card__label" for="reg-username">用户名</label>
          <div class="auth-card__input-wrapper">
            <svg
              class="auth-card__input-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <input
              id="reg-username"
              v-model="registerForm.username"
              type="text"
              class="auth-card__input"
              placeholder="请输入用户名"
              autocomplete="username"
            />
          </div>
        </div>

        <!-- 邮箱 -->
        <div class="auth-card__field">
          <label class="auth-card__label" for="reg-email">邮箱</label>
          <div class="auth-card__input-wrapper">
            <svg
              class="auth-card__input-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
              />
              <polyline points="22,6 12,13 2,6" />
            </svg>
            <input
              id="reg-email"
              v-model="registerForm.email"
              type="email"
              class="auth-card__input"
              placeholder="请输入邮箱"
              autocomplete="email"
            />
          </div>
        </div>

        <!-- 性别（下拉选择，禁止手动输入） -->
        <div class="auth-card__field">
          <label class="auth-card__label" for="reg-gender">性别</label>
          <div class="auth-card__input-wrapper">
            <svg
              class="auth-card__input-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M7 3h4v4" />
              <path d="M10 14L21 3" />
              <circle cx="7" cy="17" r="4" />
            </svg>
            <select id="reg-gender" v-model="registerForm.gender" class="auth-card__select">
              <option value="male">男</option>
              <option value="female">女</option>
              <option value="unknown">不透露</option>
            </select>
          </div>
        </div>

        <!-- 生日（下拉选择，禁止手动输入） -->
        <div class="auth-card__field">
          <label class="auth-card__label">生日</label>
          <div class="auth-card__birthday-row">
            <select
              v-model="registerForm.birthYear"
              class="auth-card__select auth-card__select--birthday"
            >
              <option value="">年</option>
              <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}</option>
            </select>
            <select
              v-model="registerForm.birthMonth"
              class="auth-card__select auth-card__select--birthday"
            >
              <option value="">月</option>
              <option v-for="month in monthOptions" :key="month" :value="month">{{ month }}</option>
            </select>
            <select
              v-model="registerForm.birthDay"
              class="auth-card__select auth-card__select--birthday"
            >
              <option value="">日</option>
              <option v-for="day in dayOptions" :key="day" :value="day">{{ day }}</option>
            </select>
          </div>
        </div>

        <!-- 密码 -->
        <div class="auth-card__field">
          <label class="auth-card__label" for="reg-password">密码</label>
          <div class="auth-card__input-wrapper">
            <svg
              class="auth-card__input-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <input
              id="reg-password"
              v-model="registerForm.password"
              :type="showRegisterPassword ? 'text' : 'password'"
              class="auth-card__input"
              placeholder="至少 6 位密码"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="auth-card__input-toggle"
              @click="showRegisterPassword = !showRegisterPassword"
              :aria-label="showRegisterPassword ? '隐藏密码' : '显示密码'"
            >
              <svg
                v-if="!showRegisterPassword"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path
                  d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 确认密码 -->
        <div class="auth-card__field">
          <label class="auth-card__label" for="reg-confirm">确认密码</label>
          <div
            class="auth-card__input-wrapper"
            :class="{ 'auth-card__input-wrapper--error': passwordMismatch }"
          >
            <svg
              class="auth-card__input-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <input
              id="reg-confirm"
              v-model="registerForm.confirmPassword"
              :type="showRegisterConfirm ? 'text' : 'password'"
              class="auth-card__input"
              placeholder="请再次输入密码"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="auth-card__input-toggle"
              @click="showRegisterConfirm = !showRegisterConfirm"
              :aria-label="showRegisterConfirm ? '隐藏密码' : '显示密码'"
            >
              <svg
                v-if="!showRegisterConfirm"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path
                  d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            </button>
          </div>
          <!-- 密码不匹配提示 -->
          <Transition name="auth-fade">
            <span v-if="passwordMismatch" class="auth-card__field-hint"> 两次密码输入不一致 </span>
          </Transition>
        </div>

        <!-- 提交按钮 -->
        <button
          type="submit"
          class="auth-card__submit"
          :disabled="isSubmitting || passwordMismatch"
        >
          <span v-if="isSubmitting" class="auth-card__spinner"></span>
          <span v-else>注 册</span>
        </button>
      </form>
    </Transition>
  </div>
</template>

<style scoped>
/* ========================================
 * 认证卡片 — 浅色玻璃拟态风格
 * ======================================== */
.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 2.5rem 2rem 2rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

/* ========================================
 * 选项卡栏
 * ======================================== */
.auth-card__tabs {
  position: relative;
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.75rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  padding-bottom: 2px;
}

.auth-card__tab {
  flex: 1;
  background: none;
  border: none;
  padding: 0.75rem 0;
  font-size: 1rem;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.35);
  cursor: pointer;
  transition: color 0.3s ease;
  font-family: inherit;
}

.auth-card__tab:hover {
  color: rgba(0, 0, 0, 0.6);
}

.auth-card__tab--active {
  color: #1a2e1a;
}

/* 选项卡底部滑动指示条 */
.auth-card__tab-indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 50%;
  height: 2px;
  background: linear-gradient(90deg, #4caf7d, #6bcf9a);
  border-radius: 1px;
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.auth-card__tab-indicator--right {
  transform: translateX(100%);
}

/* ========================================
 * 错误提示
 * ======================================== */
.auth-card__error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border-radius: 10px;
  background: rgba(220, 53, 69, 0.08);
  border: 1px solid rgba(220, 53, 69, 0.2);
  color: #c0392b;
  font-size: 0.875rem;
}

.auth-card__error-icon {
  flex-shrink: 0;
  font-size: 1rem;
}

/* ========================================
 * 表单通用样式
 * ======================================== */
.auth-card__form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* 字段组 */
.auth-card__field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.auth-card__label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.55);
  padding-left: 2px;
}

/* 输入框容器 */
.auth-card__input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  transition: all 0.25s ease;
}

.auth-card__input-wrapper:focus-within {
  border-color: rgba(76, 175, 125, 0.6);
  background: rgba(76, 175, 125, 0.04);
  box-shadow: 0 0 0 3px rgba(76, 175, 125, 0.1);
}

/* 校验失败边框 */
.auth-card__input-wrapper--error {
  border-color: rgba(220, 53, 69, 0.5) !important;
}

.auth-card__input-wrapper--error:focus-within {
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1) !important;
}

/* 左侧图标 */
.auth-card__input-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  margin-left: 14px;
  color: rgba(0, 0, 0, 0.3);
  transition: color 0.25s ease;
}

.auth-card__input-wrapper:focus-within .auth-card__input-icon {
  color: rgba(76, 175, 125, 0.8);
}

/* 输入框 */
.auth-card__input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  padding: 0.8rem 0.75rem;
  color: #1a2e1a;
  font-size: 0.9375rem;
  font-family: inherit;
}

.auth-card__input::placeholder {
  color: rgba(0, 0, 0, 0.3);
}

.auth-card__select {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  padding: 0.8rem 0.75rem;
  color: #1a2e1a;
  font-size: 0.9375rem;
  font-family: inherit;
  appearance: none;
  cursor: pointer;
}

.auth-card__birthday-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}

.auth-card__select--birthday {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.03);
}

.auth-card__select--birthday:focus {
  border-color: rgba(76, 175, 125, 0.6);
  background: rgba(76, 175, 125, 0.04);
  box-shadow: 0 0 0 3px rgba(76, 175, 125, 0.1);
}

/* 密码可见切换按钮 */
.auth-card__input-toggle {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin-right: 6px;
  background: none;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
}

.auth-card__input-toggle:hover {
  color: rgba(0, 0, 0, 0.55);
  background: rgba(0, 0, 0, 0.05);
}

.auth-card__input-toggle svg {
  width: 18px;
  height: 18px;
}

/* 字段提示 */
.auth-card__field-hint {
  font-size: 0.75rem;
  color: #c0392b;
  padding-left: 2px;
}

/* ========================================
 * 提交按钮
 * ======================================== */
.auth-card__submit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0.85rem;
  margin-top: 0.5rem;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.15em;
  color: #ffffff;
  cursor: pointer;
  font-family: inherit;

  /* 浅绿色渐变背景 */
  background: linear-gradient(135deg, #4caf7d 0%, #3d9e6e 100%);
  box-shadow: 0 4px 16px rgba(76, 175, 125, 0.3);
  transition: all 0.3s ease;
}

.auth-card__submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(76, 175, 125, 0.4);
  background: linear-gradient(135deg, #5cbf8d 0%, #4caf7d 100%);
}

.auth-card__submit:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(76, 175, 125, 0.25);
}

.auth-card__submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载旋转器 */
.auth-card__spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: auth-spin 0.7s linear infinite;
}

@keyframes auth-spin {
  to {
    transform: rotate(360deg);
  }
}

/* ========================================
 * 过渡动画
 * ======================================== */

/* 淡入淡出 */
.auth-fade-enter-active,
.auth-fade-leave-active {
  transition: opacity 0.25s ease;
}
.auth-fade-enter-from,
.auth-fade-leave-to {
  opacity: 0;
}

/* 滑入滑出（选项卡切换） */
.auth-slide-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.auth-slide-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.auth-slide-enter-from {
  opacity: 0;
  transform: translateX(16px);
}
.auth-slide-leave-to {
  opacity: 0;
  transform: translateX(-16px);
}
</style>
