/**
 * music.ts — 前端音乐领域统一模型
 *
 * 定义与后端 DTO 解耦的前端内部类型，供组件与 Store 使用。
 * 后端返回的原始数据应在 API 层转换为此处定义的模型。
 */

/** 单曲信息 */
export interface Track {
  /** 歌曲唯一标识 */
  id: string
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
