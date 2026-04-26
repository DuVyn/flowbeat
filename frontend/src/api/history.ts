import { requestJson } from '@/api/http'
import { dedup } from '@/utils/dedup'
import type {
  PlayHistoryItem,
  PlayHistoryItemDto,
  PlayHistoryResponse,
  PlayHistoryResponseDto,
  RecordPlayHistoryResponseDto,
} from '@/types/music'

function mapPlayHistoryItemDto(dto: PlayHistoryItemDto): PlayHistoryItem {
  return {
    id: dto.id,
    name: dto.name,
    artist: dto.artist,
    album: dto.album,
    coverUrl: dto.cover_url,
    durationMs: dto.duration_ms,
    playedAt: dto.played_at,
  }
}

export async function recordPlayHistory(songId: number): Promise<void> {
  await requestJson<RecordPlayHistoryResponseDto>('/api/me/history', {
    method: 'POST',
    body: JSON.stringify({
      song_id: songId,
    }),
  })
}

export async function getPlayHistory(limit = 20, offset = 0): Promise<PlayHistoryResponse> {
  const key = `history:${limit}:${offset}`
  return dedup(key, async () => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    })

    const dto = await requestJson<PlayHistoryResponseDto>(`/api/me/history?${params.toString()}`, {
      method: 'GET',
    })

    return {
      limit: dto.limit,
      offset: dto.offset,
      hasMore: dto.has_more,
      items: dto.items.map(mapPlayHistoryItemDto),
    }
  })
}
