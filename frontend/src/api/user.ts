import type { UpdateUserProfileRequest, UserProfile } from '@/types/auth'
import type {
  ListeningInsightsResponse,
  ListeningInsightsResponseDto,
  GenrePreferenceItem,
} from '@/types/music'
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

function mapGenrePreferenceItem(
  dto: ListeningInsightsResponseDto['items'][number],
): GenrePreferenceItem {
  return {
    genreCode: dto.genre_code,
    genreName: dto.genre_name,
    playCount: dto.play_count,
    weight: dto.weight,
  }
}

export async function getListeningInsights(): Promise<ListeningInsightsResponse> {
  const dto = await requestJson<ListeningInsightsResponseDto>('/api/user/insights/genres', {
    method: 'GET',
  })

  return {
    totalPlays: dto.total_plays,
    totalDistinctGenres: dto.total_distinct_genres,
    items: dto.items.map(mapGenrePreferenceItem),
  }
}
