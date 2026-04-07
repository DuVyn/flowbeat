import { defineStore } from 'pinia'

import type { AuthResponse, UserProfile } from '@/types/auth'
import { clearAuthSession, persistAuthSession, readStoredTokens } from '@/api/http'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserProfile | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: null,
    refreshToken: null,
    user: null,
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken),
  },

  actions: {
    hydrateFromStorage() {
      const { accessToken, refreshToken } = readStoredTokens()
      this.accessToken = accessToken
      this.refreshToken = refreshToken
    },

    setAuthSession(payload: AuthResponse) {
      this.accessToken = payload.access_token
      this.refreshToken = payload.refresh_token
      this.user = payload.user
      persistAuthSession(payload)
    },

    setProfile(profile: UserProfile) {
      this.user = profile
    },

    clearSession() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null
      clearAuthSession()
    },
  },
})
