/**
 * cover.ts — 封面 URL 缓存 Store
 *
 * 全局缓存歌曲封面预签名 URL，避免重复请求。
 * 页面间导航时缓存自动保留，仅当 URL 过期或应用刷新时才重置。
 * 缓存大小超过 MAX_CACHE_SIZE 时自动淘汰最老条目。
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'

import { getSongCoversBatch } from '@/api/cover'

/** 缓存条目上限，超过时淘汰最早加入的一半 */
const MAX_CACHE_SIZE = 500

/** 正在进行中的批量解析 Promise，用于合并并发请求 */
let pendingResolve: Promise<void> | null = null
let pendingIds: number[] = []

export const useCoverStore = defineStore('cover', () => {
  const cache = ref<Map<number, string>>(new Map())

  /**
   * 淘汰过多的缓存条目。
   * 使用 Map 的插入顺序特性，删除最早加入的一半。
   */
  function evictIfNeeded(): void {
    if (cache.value.size <= MAX_CACHE_SIZE) {
      return
    }
    const deleteCount = Math.floor(cache.value.size / 2)
    let deleted = 0
    for (const key of cache.value.keys()) {
      if (deleted >= deleteCount) {
        break
      }
      cache.value.delete(key)
      deleted++
    }
  }

  /**
   * 批量解析封面地址。
   *
   * 将尚未缓存的 ID 发送给后端，结果写入缓存。
   * 如果同一事件循环内多次调用，会自动合并为一次请求。
   */
  async function resolveCovers(songIds: number[]): Promise<void> {
    const uncachedIds = songIds.filter((id) => !cache.value.has(id))
    if (uncachedIds.length === 0) {
      return
    }

    // 合并同一 tick 内的多次调用
    pendingIds.push(...uncachedIds)

    if (pendingResolve) {
      return pendingResolve
    }

    pendingResolve = new Promise<void>((resolve) => {
      queueMicrotask(async () => {
        const idsToFetch = [...new Set(pendingIds)]
        pendingIds = []
        pendingResolve = null

        try {
          const result = await getSongCoversBatch(idsToFetch)
          for (const [id, url] of Object.entries(result)) {
            cache.value.set(Number(id), url)
          }
          // 对于后端未返回的 ID（无封面），也标记为空字符串避免重复请求
          for (const id of idsToFetch) {
            if (!cache.value.has(id)) {
              cache.value.set(id, '')
            }
          }
          evictIfNeeded()
        } catch {
          // 批量解析失败不应阻塞页面渲染
        }

        resolve()
      })
    })

    return pendingResolve
  }

  /**
   * 获取某首歌的封面 URL（仅读缓存，不触发请求）。
   */
  function getCoverUrl(songId: number): string {
    return cache.value.get(songId) ?? ''
  }

  return { resolveCovers, getCoverUrl, cache }
})

