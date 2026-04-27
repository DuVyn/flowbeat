/**
 * cover.ts — 批量封面地址 API
 *
 * 调用后端 POST /api/songs/covers 批量获取歌曲封面预签名 URL。
 */

import { requestJson } from '@/api/http'

interface SongCoversResponseDto {
  covers: Record<string, string>
}

const MAX_COVER_BATCH_SIZE = 100

/**
 * 批量获取歌曲封面地址。
 *
 * @param songIds - 歌曲主键 ID 数组（最多 100 个）
 * @returns song_id → presigned cover URL 的映射
 */
export async function getSongCoversBatch(songIds: number[]): Promise<Record<number, string>> {
  const uniqueValidIds = [...new Set(songIds)].filter((id) => Number.isInteger(id) && id > 0)

  if (uniqueValidIds.length === 0) {
    return {}
  }

  const result: Record<number, string> = {}

  // 后端请求模型限制 song_ids 最大 100，这里分片请求确保大列表也稳定。
  for (let i = 0; i < uniqueValidIds.length; i += MAX_COVER_BATCH_SIZE) {
    const chunk = uniqueValidIds.slice(i, i + MAX_COVER_BATCH_SIZE)
    const dto = await requestJson<SongCoversResponseDto>('/api/songs/covers', {
      method: 'POST',
      body: JSON.stringify({ song_ids: chunk }),
    })

    for (const [key, url] of Object.entries(dto.covers)) {
      result[Number(key)] = url
    }
  }

  return result
}
