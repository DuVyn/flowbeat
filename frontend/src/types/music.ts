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
  /** 封面图片 URL */
  coverUrl: string
  /** 播放时长（毫秒） */
  durationMs: number
  /** 当前用户是否已收藏 */
  isLiked: boolean
}

/** 后端 Track DTO（snake_case） */
export interface TrackDto {
  id: number
  song_id: string
  name: string
  artist: string
  cover_url: string
  duration_ms: number
  is_liked: boolean
}

/** 推荐来源策略 */
export type RecommendationStrategy = 'two_tower' | 'content_cold_start' | 'global_hot'

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

/** 个性化推荐分页响应 DTO */
export interface PersonalizedRecommendationsResponseDto {
  strategy: RecommendationStrategy
  limit: number
  offset: number
  total: number
  items: TrackDto[]
}

/** 前端可直接使用的个性化推荐响应 */
export interface PersonalizedRecommendationsResponse {
  strategy: RecommendationStrategy
  limit: number
  offset: number
  total: number
  items: Track[]
}

/** 歌曲搜索分页响应 DTO */
export interface SongSearchResponseDto {
  query: string
  limit: number
  offset: number
  has_more: boolean
  items: TrackDto[]
}

/** 前端可直接使用的歌曲搜索分页响应 */
export interface SongSearchResponse {
  query: string
  limit: number
  offset: number
  hasMore: boolean
  items: Track[]
}

/** 单曲详情 DTO */
export interface SongDetailResponseDto extends TrackDto {
  language: number | null
  audio_object_key: string | null
}

/** 收藏歌曲条目 DTO */
export interface FavoriteTrackItemDto extends TrackDto {
  favorited_at: string
}

/** 收藏歌曲条目 */
export interface FavoriteTrackItem extends Track {
  favoritedAt: string
}

/** 收藏列表响应 DTO */
export interface FavoriteSongsResponseDto {
  limit: number
  offset: number
  has_more: boolean
  items: FavoriteTrackItemDto[]
}

/** 收藏列表响应 */
export interface FavoriteSongsResponse {
  limit: number
  offset: number
  hasMore: boolean
  items: FavoriteTrackItem[]
}

/** 收藏切换响应 DTO */
export interface FavoriteToggleResponseDto {
  song_id: number
  is_liked: boolean
  detail: string
}

/** 收藏切换响应 */
export interface FavoriteToggleResponse {
  songId: number
  isLiked: boolean
  detail: string
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

/** 记录播放历史请求 DTO */
export interface RecordPlayHistoryRequestDto {
  song_id: number
}

/** 记录播放历史响应 DTO */
export interface RecordPlayHistoryResponseDto {
  detail: string
}

/** 播放历史单条 DTO */
export interface PlayHistoryItemDto extends TrackDto {
  played_at: string
}

/** 播放历史分页响应 DTO */
export interface PlayHistoryResponseDto {
  limit: number
  offset: number
  has_more: boolean
  items: PlayHistoryItemDto[]
}

/** 前端可直接使用的播放历史单条 */
export interface PlayHistoryItem extends Track {
  playedAt: string
}

/** 前端可直接使用的播放历史分页响应 */
export interface PlayHistoryResponse {
  limit: number
  offset: number
  hasMore: boolean
  items: PlayHistoryItem[]
}

/** 流派偏好条目 DTO */
export interface GenrePreferenceItem {
  genreCode: string
  genreName: string
  playCount: number
  weight: number
}

/** 流派偏好条目 DTO */
export interface GenrePreferenceItemDto {
  genre_code: string
  genre_name: string
  play_count: number
  weight: number
}

/** 首页偏好画像响应 */
export interface ListeningInsightsResponse {
  totalPlays: number
  totalDistinctGenres: number
  items: GenrePreferenceItem[]
}

/** 首页偏好画像响应 DTO */
export interface ListeningInsightsResponseDto {
  total_plays: number
  total_distinct_genres: number
  items: GenrePreferenceItemDto[]
}

/** 流派目录条目 */
export interface GenreCatalogItem {
  genreCode: string
  genreName: string
  songCount: number
}

/** 流派目录条目 DTO */
export interface GenreCatalogItemDto {
  genre_code: string
  genre_name: string
  song_count: number
}

/** 流派目录响应 */
export interface GenreCatalogResponse {
  items: GenreCatalogItem[]
}

/** 流派目录响应 DTO */
export interface GenreCatalogResponseDto {
  items: GenreCatalogItemDto[]
}

/** 通用歌曲 Feed 响应 */
export interface SongFeedResponse {
  title: string
  limit: number
  offset: number
  hasMore: boolean
  genreCode: string | null
  genreName: string | null
  items: Track[]
}

/** 通用歌曲 Feed 响应 DTO */
export interface SongFeedResponseDto {
  title: string
  limit: number
  offset: number
  has_more: boolean
  genre_code: string | null
  genre_name: string | null
  items: TrackDto[]
}

/** 清空播放历史响应 */
export interface ClearPlayHistoryResponse {
  detail: string
  deletedCount: number
}

/** 清空播放历史响应 DTO */
export interface ClearPlayHistoryResponseDto {
  detail: string
  deleted_count: number
}
