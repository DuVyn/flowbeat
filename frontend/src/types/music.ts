/**
 * music.ts — 前端音乐领域统一模型
 *
 * 定义与后端 DTO 解耦的前端内部类型，供组件与 Store 使用。
 * 后端返回的原始数据应在 API 层转换为此处定义的模型。
 */

/** 单曲信息 */
export interface Track {
  /** 歌曲唯一标识 */
  id: number
  /** 歌曲名称 */
  name: string
  /** 艺术家（主歌手 / 乐队名） */
  artist: string
  /** 所属专辑名称 */
  album: string
  /** 封面图片 URL */
  coverUrl: string
  /** 播放时长（毫秒） */
  durationMs: number
}

/** 后端 Track DTO（snake_case） */
export interface TrackDto {
  id: number
  song_id: string
  name: string
  artist: string
  album: string
  cover_url: string
  duration_ms: number
}

/** 热门推荐分页响应 DTO */
export interface HotRecommendationsResponseDto {
  strategy: 'global_hot'
  limit: number
  offset: number
  total: number
  items: TrackDto[]
}

/** 前端可直接使用的热门推荐响应 */
export interface HotRecommendationsResponse {
  strategy: 'global_hot'
  limit: number
  offset: number
  total: number
  items: Track[]
}

/** 单曲详情 DTO */
export interface SongDetailResponseDto extends TrackDto {
  language: number | null
  audio_object_key: string | null
}

/** 单曲流地址 DTO */
export interface SongStreamResponseDto {
  song_id: number
  stream_url: string
  expires_in_seconds: number
  strategy: 'minio_presigned_url'
}

/** 前端可直接使用的单曲流地址 */
export interface SongStreamResponse {
  songId: number
  streamUrl: string
  expiresInSeconds: number
  strategy: 'minio_presigned_url'
}

/** 歌单 / 播放列表 */
export interface Playlist {
  /** 歌单唯一标识 */
  id: string
  /** 歌单标题 */
  title: string
  /** 歌单描述 */
  description: string
  /** 歌单封面 URL */
  coverUrl: string
  /** 包含的曲目列表 */
  tracks: Track[]
  /** 歌曲总数 */
  trackCount: number
}

/** 专辑信息 */
export interface Album {
  /** 专辑唯一标识 */
  id: string
  /** 专辑名称 */
  name: string
  /** 专辑封面 URL */
  coverUrl: string
  /** 艺术家 */
  artist: string
  /** 发行年份 */
  year: number
  /** 包含的曲目列表 */
  tracks: Track[]
}
