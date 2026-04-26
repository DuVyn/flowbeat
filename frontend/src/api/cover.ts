/**
 * cover.ts — 批量封面地址 API
 *
 * 调用后端 POST /api/songs/covers 批量获取歌曲封面预签名 URL。
 */

import { requestJson } from '@/api/http'

interface SongCoversResponseDto {
  covers: Record<string, string>
}

/**
 * 批量获取歌曲封面地址。
 *
 * @param songIds - 歌曲主键 ID 数组（最多 100 个）
 * @returns song_id → presigned cover URL 的映射
 */
export async function getSongCoversBatch(
  songIds: number[],
): Promise<Record<number, string>> {
  if (songIds.length === 0) {
    return {}
  }

  const dto = await requestJson<SongCoversResponseDto>('/api/songs/covers', {
    method: 'POST',
    body: JSON.stringify({ song_ids: songIds }),
  })

  const result: Record<number, string> = {}
  for (const [key, url] of Object.entries(dto.covers)) {
    result[Number(key)] = url
  }
  return result
}
