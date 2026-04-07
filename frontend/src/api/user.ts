import type { UpdateUserProfileRequest, UserProfile } from '@/types/auth'
import { requestJson } from '@/api/http'

export async function getUserProfile(): Promise<UserProfile> {
  return requestJson<UserProfile>('/api/user/profile', {
    method: 'GET',
  })
}

export async function updateUserProfile(payload: UpdateUserProfileRequest): Promise<UserProfile> {
  return requestJson<UserProfile>('/api/user/profile', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
