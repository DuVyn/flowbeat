<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { HttpError } from '@/api/http'
import { getGenreCatalog } from '@/api/genres'
import { getUserPreferredGenres, updateUserPreferredGenres } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import type { GenreCatalogItem } from '@/types/music'

const authStore = useAuthStore()

const isOpen = ref(false)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const genres = ref<GenreCatalogItem[]>([])
const selectedCodes = ref<string[]>([])

const selectedCount = computed(() => selectedCodes.value.length)
const canSubmit = computed(() => selectedCount.value > 0 && !isLoading.value && !isSaving.value)

function resetState() {
  isOpen.value = false
  isLoading.value = false
  isSaving.value = false
  errorMessage.value = ''
  selectedCodes.value = []
}

async function loadGenreCatalog() {
  if (genres.value.length > 0) {
    return
  }

  try {
    const response = await getGenreCatalog()
    genres.value = response.items
  } catch (error) {
    errorMessage.value = error instanceof HttpError ? error.detail : '无法读取流派目录，请稍后重试'
  }
}

async function loadPreferenceState() {
  authStore.hydrateFromStorage()
  if (!authStore.isAuthenticated) {
    resetState()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await getUserPreferredGenres()
    selectedCodes.value = response.genreCodes

    if (response.genreCodes.length === 0) {
      isOpen.value = true
      await loadGenreCatalog()
    } else {
      isOpen.value = false
    }
  } catch (error) {
    isOpen.value = true
    errorMessage.value = error instanceof HttpError ? error.detail : '无法读取偏好流派，请稍后重试'
    await loadGenreCatalog()
  } finally {
    isLoading.value = false
  }
}

function toggleGenre(code: string) {
  if (isLoading.value || isSaving.value) {
    return
  }

  if (selectedCodes.value.includes(code)) {
    selectedCodes.value = selectedCodes.value.filter((item) => item !== code)
    return
  }

  selectedCodes.value = [...selectedCodes.value, code]
}

async function handleSubmit() {
  if (!canSubmit.value) {
    errorMessage.value = '至少选择 1 个流派'
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    const response = await updateUserPreferredGenres({
      genreCodes: selectedCodes.value,
    })
    selectedCodes.value = response.genreCodes
    isOpen.value = false
  } catch (error) {
    errorMessage.value = error instanceof HttpError ? error.detail : '保存偏好失败，请稍后重试'
  } finally {
    isSaving.value = false
  }
}

watch(
  () => authStore.accessToken,
  (token) => {
    if (token) {
      void loadPreferenceState()
      return
    }

    resetState()
  },
  { immediate: true },
)
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="genre-modal" role="dialog" aria-modal="true">
      <div class="genre-modal__backdrop"></div>
      <div class="genre-modal__dialog" aria-labelledby="genre-preference-title">
        <header class="genre-modal__header">
          <p class="genre-modal__eyebrow">新用户必选</p>
          <h2 id="genre-preference-title" class="genre-modal__title">选择你的偏好流派</h2>
          <p class="genre-modal__subtitle">系统将据此生成推荐，至少选择 1 个。</p>
        </header>

        <section class="genre-modal__body">
          <div v-if="isLoading" class="genre-modal__loading">正在读取流派目录...</div>
          <div v-else-if="genres.length === 0" class="genre-modal__empty">
            暂无可选流派，请稍后重试。
          </div>
          <div v-else class="genre-modal__grid">
            <button
              v-for="genre in genres"
              :key="genre.genreCode"
              type="button"
              class="genre-modal__chip"
              :class="{ 'genre-modal__chip--active': selectedCodes.includes(genre.genreCode) }"
              :aria-pressed="selectedCodes.includes(genre.genreCode)"
              @click="toggleGenre(genre.genreCode)"
            >
              <span class="genre-modal__chip-name">{{ genre.genreName }}</span>
              <span class="genre-modal__chip-meta">{{ genre.songCount }} 首</span>
            </button>
          </div>
        </section>

        <footer class="genre-modal__footer">
          <div class="genre-modal__status">
            <span class="genre-modal__count">已选 {{ selectedCount }} 个</span>
            <span v-if="errorMessage" class="genre-modal__error">{{ errorMessage }}</span>
          </div>
          <button
            type="button"
            class="genre-modal__submit"
            :disabled="!canSubmit"
            @click="handleSubmit"
          >
            <span v-if="isSaving" class="genre-modal__spinner"></span>
            <span v-else>保存偏好</span>
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.genre-modal {
  position: fixed;
  inset: 0;
  z-index: 2400;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.genre-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(18, 32, 22, 0.38);
  backdrop-filter: blur(8px);
}

.genre-modal__dialog {
  position: relative;
  width: min(720px, 100%);
  max-height: min(82vh, 760px);
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 22px;
  box-shadow:
    0 24px 70px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.genre-modal__header {
  padding: 1.75rem 2rem 1.25rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.genre-modal__eyebrow {
  margin: 0 0 0.5rem;
  font-size: 0.75rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: rgba(26, 46, 26, 0.5);
}

.genre-modal__title {
  margin: 0 0 0.5rem;
  font-size: 1.6rem;
  font-weight: 700;
  color: #1a2e1a;
}

.genre-modal__subtitle {
  margin: 0;
  font-size: 0.95rem;
  color: rgba(26, 46, 26, 0.65);
}

.genre-modal__body {
  padding: 1.25rem 2rem 0.5rem;
  flex: 1;
  overflow: hidden;
}

.genre-modal__loading,
.genre-modal__empty {
  padding: 2rem 0;
  text-align: center;
  color: rgba(26, 46, 26, 0.6);
}

.genre-modal__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
  max-height: 360px;
  overflow: auto;
  padding-right: 0.25rem;
}

.genre-modal__chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  padding: 0.85rem 0.9rem;
  border-radius: 14px;
  border: 1px solid rgba(76, 175, 125, 0.2);
  background: rgba(76, 175, 125, 0.08);
  color: rgba(26, 46, 26, 0.85);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.genre-modal__chip:hover {
  transform: translateY(-1px);
  border-color: rgba(76, 175, 125, 0.45);
  box-shadow: 0 6px 16px rgba(76, 175, 125, 0.15);
}

.genre-modal__chip--active {
  background: linear-gradient(135deg, rgba(76, 175, 125, 0.9), rgba(60, 158, 110, 0.85));
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 10px 20px rgba(60, 158, 110, 0.3);
}

.genre-modal__chip-name {
  font-weight: 600;
}

.genre-modal__chip-meta {
  font-size: 0.75rem;
  opacity: 0.8;
}

.genre-modal__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 2rem 1.75rem;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.genre-modal__status {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.genre-modal__count {
  font-size: 0.85rem;
  color: rgba(26, 46, 26, 0.6);
}

.genre-modal__error {
  font-size: 0.85rem;
  color: #c0392b;
}

.genre-modal__submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 140px;
  padding: 0.75rem 1.5rem;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #4caf7d, #3d9e6e);
  color: #ffffff;
  font-weight: 600;
  letter-spacing: 0.12em;
  cursor: pointer;
  transition: all 0.2s ease;
}

.genre-modal__submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(76, 175, 125, 0.35);
}

.genre-modal__submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.genre-modal__spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: genre-spin 0.7s linear infinite;
}

@keyframes genre-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .genre-modal {
    padding: 1rem;
  }

  .genre-modal__dialog {
    max-height: 86vh;
  }

  .genre-modal__header,
  .genre-modal__body,
  .genre-modal__footer {
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }

  .genre-modal__grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    max-height: 300px;
  }

  .genre-modal__footer {
    flex-direction: column;
    align-items: stretch;
  }

  .genre-modal__submit {
    width: 100%;
  }
}
</style>
