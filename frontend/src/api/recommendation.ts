import { requestJson } from '@/api/http'
import type {
  HotRecommendationsResponse,
  HotRecommendationsResponseDto,
  Track,
  TrackDto,
} from '@/types/music'

function mapTrackDto(dto: TrackDto): Track {
  return {
    id: dto.id,
    name: dto.name,
    artist: dto.artist,
    album: dto.album,
    coverUrl: dto.cover_url,
    durationMs: dto.duration_ms,
  }
}

export async function getHotRecommendations(
  limit = 20,
  offset = 0,
): Promise<HotRecommendationsResponse> {
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
}
