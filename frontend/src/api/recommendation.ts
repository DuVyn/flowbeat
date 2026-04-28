import { requestJson } from '@/api/http'
import { dedup } from '@/utils/dedup'
import type {
  HotRecommendationsResponse,
  HotRecommendationsResponseDto,
  PersonalizedRecommendationsResponse,
  PersonalizedRecommendationsResponseDto,
  Track,
  TrackDto,
} from '@/types/music'

function mapTrackDto(dto: TrackDto): Track {
  return {
    id: dto.id,
    name: dto.name,
    artist: dto.artist,
    coverUrl: dto.cover_url,
    durationMs: dto.duration_ms,
    isLiked: dto.is_liked,
  }
}

export async function getHotRecommendations(
  limit = 20,
  offset = 0,
): Promise<HotRecommendationsResponse> {
  const key = `hot:${limit}:${offset}`
  return dedup(key, async () => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    })
    const dto = await requestJson<HotRecommendationsResponseDto>(
      `/api/recommendations/hot?${params.toString()}`,
      {
        method: 'GET',
      },
    )

    return {
      strategy: dto.strategy,
      limit: dto.limit,
      offset: dto.offset,
      total: dto.total,
      items: dto.items.map(mapTrackDto),
    }
  })
}

export async function getPersonalizedRecommendations(
  limit = 20,
  offset = 0,
): Promise<PersonalizedRecommendationsResponse> {
  const key = `personalized:${limit}:${offset}`
  return dedup(key, async () => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    })

    const dto = await requestJson<PersonalizedRecommendationsResponseDto>(
      `/api/recommendations/personalized?${params.toString()}`,
      {
        method: 'GET',
      },
    )

    return {
      strategy: dto.strategy,
      limit: dto.limit,
      offset: dto.offset,
      total: dto.total,
      items: dto.items.map(mapTrackDto),
    }
  })
}

export async function getContentRecommendations(
  limit = 20,
  offset = 0,
): Promise<PersonalizedRecommendationsResponse> {
  const key = `content:${limit}:${offset}`
  return dedup(key, async () => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    })

    const dto = await requestJson<PersonalizedRecommendationsResponseDto>(
      `/api/recommendations/content?${params.toString()}`,
      {
        method: 'GET',
      },
    )

    return {
      strategy: dto.strategy,
      limit: dto.limit,
      offset: dto.offset,
      total: dto.total,
      items: dto.items.map(mapTrackDto),
    }
  })
}
