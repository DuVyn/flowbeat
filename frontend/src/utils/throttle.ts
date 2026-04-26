/**
 * throttle.ts — 节流工具函数
 *
 * 限制函数在指定时间间隔内最多执行一次。
 */

export function throttle<T extends (...args: unknown[]) => void>(
  fn: T,
  intervalMs: number,
): T {
  let lastCall = 0
  let timer: ReturnType<typeof setTimeout> | null = null

  const throttled = (...args: unknown[]) => {
    const now = Date.now()
    const remaining = intervalMs - (now - lastCall)

    if (remaining <= 0) {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      lastCall = now
      fn(...args)
    } else if (!timer) {
      timer = setTimeout(() => {
        lastCall = Date.now()
        timer = null
        fn(...args)
      }, remaining)
    }
  }

  return throttled as unknown as T
}
