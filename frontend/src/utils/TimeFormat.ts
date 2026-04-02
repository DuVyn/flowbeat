/**
 * TimeFormat.ts — 时间格式化工具
 *
 * 封装无状态的纯函数，不依赖任何外部状态或 Vue 实例。
 * 后端 API 返回毫秒数，须转换为 mm:ss 格式的字符串，供展示层组件直接调用。
 */

/**
 * 将毫秒数转换为 mm:ss 格式字符串。
 *
 * @param ms - 播放时长（毫秒），非负整数
 * @returns 格式化后的字符串，如 "4:29"、"0:05"、"12:00"
 *
 * @example
 * ```ts
 * formatDuration(269000) // => "4:29"
 * formatDuration(5000)   // => "0:05"
 * formatDuration(0)      // => "0:00"
 * ```
 */
export function formatDuration(ms: number): string {
  if (ms < 0 || !Number.isFinite(ms)) {
    return '0:00'
  }

  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60

  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}
