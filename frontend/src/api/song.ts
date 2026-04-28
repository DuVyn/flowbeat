import { requestJson } from '@/api/http'
import type {
  SongSearchResponse,
  SongSearchResponseDto,
  SongDetailResponseDto,
  SongFeedResponse,
  SongFeedResponseDto,
  SongStreamResponse,
  SongStreamResponseDto,
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

export async function searchSongs(
  query: string,
  limit = 20,
  offset = 0,
): Promise<SongSearchResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  })

  const dto = await requestJson<SongSearchResponseDto>(`/api/songs/search?${params.toString()}`, {
    method: 'GET',
  })

  return {
    query: dto.query,
    limit: dto.limit,
    offset: dto.offset,
    hasMore: dto.has_more,
    items: dto.items.map(mapTrackDto),
  }
}

export async function getSongStream(songId: number): Promise<SongStreamResponse> {
  const dto = await requestJson<SongStreamResponseDto>(`/api/songs/${songId}/stream`, {
    method: 'GET',
  })

  return {
    songId: dto.song_id,
    streamUrl: dto.stream_url,
    expiresInSeconds: dto.expires_in_seconds,
    strategy: dto.strategy,
  }
}

export async function getSongDetail(songId: number): Promise<Track> {
  const dto = await requestJson<SongDetailResponseDto>(`/api/songs/${songId}/detail`, {
    method: 'GET',
  })

  return mapTrackDto(dto)
}

export async function getLatestSongs(limit = 20, offset = 0): Promise<SongFeedResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  const dto = await requestJson<SongFeedResponseDto>(`/api/songs/latest?${params.toString()}`, {
    method: 'GET',
  })

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
