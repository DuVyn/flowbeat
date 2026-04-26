<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { HttpError } from '@/api/http'
import { getUserProfile, updateUserProfile } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import type { GenderValue, UpdateUserProfileRequest, UserProfile } from '@/types/auth'

const authStore = useAuthStore()

const loading = ref(true)
const saving = ref(false)
const isEditing = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const profile = ref<UserProfile | null>(null)

const form = reactive({
  username: '',
  gender: 'unknown' as GenderValue,
  birthYear: '',
  birthMonth: '',
  birthDay: '',
})

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 100 }, (_, index) => String(currentYear - index))
const monthOptions = Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, '0'))

const dayOptions = computed(() => {
  const year = Number(form.birthYear || currentYear)
  const month = Number(form.birthMonth || 1)
  const daysInMonth = new Date(year, month, 0).getDate()
  return Array.from({ length: daysInMonth }, (_, index) => String(index + 1).padStart(2, '0'))
})

const birthday = computed(() => {
  if (!form.birthYear || !form.birthMonth || !form.birthDay) {
    return null
  }
  return `${form.birthYear}-${form.birthMonth}-${form.birthDay}`
})

const registrationTimeText = computed(() => {
  if (!profile.value?.registration_init_time) {
    return '暂无'
  }
  return new Date(profile.value.registration_init_time).toLocaleString('zh-CN')
})

const genderText = computed(() => {
  switch (profile.value?.gender) {
    case 'male':
      return '男'
    case 'female':
      return '女'
    default:
      return '不透露'
  }
})

function resetFormFromProfile(userProfile: UserProfile | null) {
  if (!userProfile) {
    return
  }
  form.username = userProfile.username
  form.gender = userProfile.gender
  form.birthYear = ''
  form.birthMonth = ''
  form.birthDay = ''
}

function startEditing() {
  if (!profile.value) {
    return
  }
  resetFormFromProfile(profile.value)
  errorMessage.value = ''
  successMessage.value = ''
  isEditing.value = true
}

function cancelEditing() {
  resetFormFromProfile(profile.value)
  errorMessage.value = ''
  successMessage.value = ''
  isEditing.value = false
}

async function loadProfile() {
  loading.value = true
  errorMessage.value = ''

  try {
    const data = await getUserProfile()
    profile.value = data
    resetFormFromProfile(data)
    authStore.setProfile(data)
  } catch (error) {
    if (error instanceof HttpError) {
      errorMessage.value = error.detail
      return
    }
    errorMessage.value = '加载个人资料失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function submitProfileUpdate() {
  if (!profile.value || !isEditing.value) {
    return
  }

  errorMessage.value = ''
  successMessage.value = ''

  const payload: UpdateUserProfileRequest = {}

  const trimmedUsername = form.username.trim()
  if (trimmedUsername && trimmedUsername !== profile.value.username) {
    payload.username = trimmedUsername
  }
  if (form.gender !== profile.value.gender) {
    payload.gender = form.gender
  }
  if (birthday.value) {
    payload.birthday = birthday.value
  }

  if (!payload.username && !payload.gender && !payload.birthday) {
    successMessage.value = '没有可提交的变更'
    return
  }

  saving.value = true
  try {
    const updated = await updateUserProfile(payload)
    profile.value = updated
    authStore.setProfile(updated)
    successMessage.value = '资料更新成功'
    resetFormFromProfile(updated)
    isEditing.value = false
  } catch (error) {
    if (error instanceof HttpError) {
      errorMessage.value = error.detail
      return
    }
    errorMessage.value = '资料更新失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void loadProfile()
})
</script>

<template>
  <section class="profile-page">
    <header class="profile-page__header">
      <h1>个人中心</h1>
      <p>维护你的用户名、性别与年龄信息</p>
    </header>

    <div v-if="loading" class="profile-page__status">资料加载中...</div>

    <div v-else class="profile-card">
      <div class="profile-card__actions">
        <button
          v-if="!isEditing"
          class="profile-card__action-button"
          type="button"
          @click="startEditing"
        >
          修改信息
        </button>
        <button
          v-else
          class="profile-card__action-button profile-card__action-button--secondary"
          type="button"
          @click="cancelEditing"
        >
          取消修改
        </button>
      </div>

      <div v-if="errorMessage" class="profile-card__error">{{ errorMessage }}</div>
      <div v-if="successMessage" class="profile-card__success">{{ successMessage }}</div>

      <div class="profile-card__static-row">
        <div>
          <label>用户名</label>
          <p>{{ profile?.username ?? '-' }}</p>
        </div>
        <div>
          <label>性别</label>
          <p>{{ genderText }}</p>
        </div>
      </div>

      <div class="profile-card__static-row">
        <div>
          <label>邮箱</label>
          <p>{{ profile?.email ?? '-' }}</p>
        </div>
        <div>
          <label>当前年龄</label>
          <p>{{ profile?.age ?? '-' }}</p>
        </div>
      </div>

      <div class="profile-card__static-row">
        <div>
          <label>注册时间</label>
          <p>{{ registrationTimeText }}</p>
        </div>
      </div>

      <p v-if="!isEditing" class="profile-card__read-tip">点击“修改信息”后可编辑资料。</p>

      <form v-if="isEditing" class="profile-card__form" @submit.prevent="submitProfileUpdate">
        <div class="profile-card__field">
          <label for="username">用户名</label>
          <input id="username" v-model="form.username" type="text" maxlength="255" />
        </div>

        <div class="profile-card__field">
          <label for="gender">性别</label>
          <select id="gender" v-model="form.gender">
            <option value="male">男</option>
            <option value="female">女</option>
            <option value="unknown">不透露</option>
          </select>
        </div>

        <div class="profile-card__field">
          <label>生日（可选，提交后自动重算年龄）</label>
          <div class="profile-card__birthday-selects">
            <select v-model="form.birthYear">
              <option value="">年</option>
              <option v-for="year in yearOptions" :key="year" :value="year">{{ year }}</option>
            </select>
            <select v-model="form.birthMonth">
              <option value="">月</option>
              <option v-for="month in monthOptions" :key="month" :value="month">{{ month }}</option>
            </select>
            <select v-model="form.birthDay">
              <option value="">日</option>
              <option v-for="day in dayOptions" :key="day" :value="day">{{ day }}</option>
            </select>
          </div>
        </div>

        <button class="profile-card__submit" type="submit" :disabled="saving">
          {{ saving ? '保存中...' : '保存资料' }}
        </button>
      </form>
    </div>
  </section>
</template>

<style scoped>
.profile-page {
  color: #1a2e1a;
}

.profile-page__header {
  margin-bottom: 1.2rem;
}

.profile-page__header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.profile-page__header p {
  margin: 0.5rem 0 0;
  color: rgba(0, 0, 0, 0.5);
}

.profile-page__status {
  padding: 1rem;
  border-radius: 10px;
  background: #ffffff;
}

.profile-card {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  padding: 1.25rem;
}

.profile-card__actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.8rem;
}

.profile-card__action-button {
  border: none;
  border-radius: 10px;
  padding: 0.58rem 0.92rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #4caf7d, #3d9e6e);
  cursor: pointer;
}

.profile-card__action-button--secondary {
  color: #2f4f3f;
  background: rgba(76, 175, 125, 0.16);
}

.profile-card__error,
.profile-card__success {
  margin-bottom: 0.8rem;
  border-radius: 10px;
  padding: 0.6rem 0.8rem;
  font-size: 0.875rem;
}

.profile-card__error {
  color: #c0392b;
  background: rgba(220, 53, 69, 0.08);
}

.profile-card__success {
  color: #1f7a4a;
  background: rgba(76, 175, 125, 0.12);
}

.profile-card__static-row {
  display: grid;
  gap: 0.8rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  margin-bottom: 0.9rem;
}

.profile-card__static-row label,
.profile-card__field label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.8rem;
  color: rgba(0, 0, 0, 0.55);
}

.profile-card__static-row p {
  margin: 0;
  font-size: 0.95rem;
}

.profile-card__read-tip {
  margin: 0.2rem 0 0;
  color: rgba(0, 0, 0, 0.5);
  font-size: 0.9rem;
}

.profile-card__form {
  display: grid;
  gap: 0.9rem;
}

.profile-card__field input,
.profile-card__field select {
  width: 100%;
  border: 1px solid rgba(0, 0, 0, 0.14);
  border-radius: 10px;
  padding: 0.58rem 0.72rem;
  font-size: 0.92rem;
  background: #ffffff;
}

.profile-card__field input:focus,
.profile-card__field select:focus {
  border-color: rgba(76, 175, 125, 0.6);
  box-shadow: 0 0 0 3px rgba(76, 175, 125, 0.12);
  outline: none;
}

.profile-card__birthday-selects {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.6rem;
}

.profile-card__submit {
  border: none;
  border-radius: 10px;
  padding: 0.72rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #4caf7d, #3d9e6e);
  cursor: pointer;
}

.profile-card__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
