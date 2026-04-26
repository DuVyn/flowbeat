/**
 * dedup.ts — 请求去重工具
 *
 * 对完全相同的异步请求进行去重：如果同一个 key 的请求正在进行中，
 * 后续的调用将复用已有的 Promise，而不是发起新请求。
 */

const inflightMap = new Map<string, Promise<unknown>>()

/**
 * 如果 key 对应的请求正在进行中，返回已有 Promise；否则执行 fn 并缓存 Promise。
 *
 * 请求完成（无论成功或失败）后自动清除缓存。
 */
export function dedup<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = inflightMap.get(key) as Promise<T> | undefined
  if (existing) {
    return existing
  }

  const promise = fn().finally(() => {
    inflightMap.delete(key)
  })

  inflightMap.set(key, promise)
  return promise
}
