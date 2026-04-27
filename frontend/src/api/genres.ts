import { requestJson } from '@/api/http'
import type {
  GenreCatalogItem,
  GenreCatalogItemDto,
  GenreCatalogResponse,
  GenreCatalogResponseDto,
  SongFeedResponse,
  SongFeedResponseDto,
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
  }
}

function mapGenreCatalogItem(dto: GenreCatalogItemDto): GenreCatalogItem {
  return {
    genreCode: dto.genre_code,
    genreName: dto.genre_name,
    songCount: dto.song_count,
  }
}

export async function getGenreCatalog(): Promise<GenreCatalogResponse> {
  const dto = await requestJson<GenreCatalogResponseDto>('/api/genres', {
    method: 'GET',
  })

  return {
    items: dto.items.map(mapGenreCatalogItem),
  }
}

export async function getGenreSongs(
  genreCode: string,
  limit = 20,
  offset = 0,
): Promise<SongFeedResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  const dto = await requestJson<SongFeedResponseDto>(
    `/api/genres/${encodeURIComponent(genreCode)}/songs?${params.toString()}`,
    {
      method: 'GET',
    },
  )

  return {
    title: dto.title,
    limit: dto.limit,
    offset: dto.offset,
    hasMore: dto.has_more,
    genreCode: dto.genre_code,
    genreName: dto.genre_name,
    items: dto.items.map(mapTrackDto),
  }
}
