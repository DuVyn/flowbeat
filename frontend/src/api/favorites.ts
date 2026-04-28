import { requestJson } from '@/api/http'
import type {
  FavoriteSongsResponse,
  FavoriteSongsResponseDto,
  FavoriteToggleResponse,
  FavoriteToggleResponseDto,
  FavoriteTrackItem,
  FavoriteTrackItemDto,
} from '@/types/music'

function mapFavoriteTrackItemDto(dto: FavoriteTrackItemDto): FavoriteTrackItem {
  return {
    id: dto.id,
    name: dto.name,
    artist: dto.artist,
    coverUrl: dto.cover_url,
    durationMs: dto.duration_ms,
    isLiked: dto.is_liked,
    favoritedAt: dto.favorited_at,
  }
}

export async function toggleFavorite(songId: number): Promise<FavoriteToggleResponse> {
  const dto = await requestJson<FavoriteToggleResponseDto>(`/api/me/favorites/${songId}/toggle`, {
    method: 'POST',
  })

  return {
    songId: dto.song_id,
    isLiked: dto.is_liked,
    detail: dto.detail,
  }
}

export async function getFavoriteSongs(limit = 20, offset = 0): Promise<FavoriteSongsResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  const dto = await requestJson<FavoriteSongsResponseDto>(
    `/api/me/favorites?${params.toString()}`,
    {
      method: 'GET',
    },
  )

  return {
    limit: dto.limit,
    offset: dto.offset,
    hasMore: dto.has_more,
    items: dto.items.map(mapFavoriteTrackItemDto),
  }
}
