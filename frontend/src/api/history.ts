import { HttpError, requestJson } from '@/api/http'
import { dedup } from '@/utils/dedup'
import type {
  ClearPlayHistoryResponse,
  ClearPlayHistoryResponseDto,
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
    coverUrl: dto.cover_url,
    durationMs: dto.duration_ms,
    isLiked: dto.is_liked,
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

export async function getLatestPlayHistory(): Promise<PlayHistoryItem | null> {
  try {
    const dto = await requestJson<PlayHistoryItemDto>('/api/me/history/latest', {
      method: 'GET',
    })
    return mapPlayHistoryItemDto(dto)
  } catch (error) {
    if (error instanceof HttpError && error.status === 404) {
      return null
    }
    throw error
  }
}

export async function clearPlayHistory(): Promise<ClearPlayHistoryResponse> {
  const dto = await requestJson<ClearPlayHistoryResponseDto>('/api/me/history', {
    method: 'DELETE',
  })

  return {
    detail: dto.detail,
    deletedCount: dto.deleted_count,
  }
}
