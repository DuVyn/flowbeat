import { requestJson } from '@/api/http'
import type {
  SongDetailResponseDto,
  SongStreamResponse,
  SongStreamResponseDto,
  Track,
} from '@/types/music'

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

  return {
    id: dto.id,
    name: dto.name,
    artist: dto.artist,
    album: dto.album,
    coverUrl: dto.cover_url,
    durationMs: dto.duration_ms,
  }
}
