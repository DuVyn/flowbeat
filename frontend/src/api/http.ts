import type { AuthResponse } from '@/types/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const ACCESS_TOKEN_KEY = 'flowbeat_access_token'
const REFRESH_TOKEN_KEY = 'flowbeat_refresh_token'

interface TokenPayload {
  exp?: unknown
}

export class HttpError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

interface RequestConfig extends RequestInit {
  skipAuth?: boolean
}

function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

function buildUrl(path: string): string {
  if (!path.startsWith('/')) {
    return `${API_BASE_URL}/${path}`
  }
  return `${API_BASE_URL}${path}`
}

export async function requestJson<T>(path: string, config: RequestConfig = {}): Promise<T> {
  const headers = new Headers(config.headers)
  headers.set('Accept', 'application/json')

  if (config.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (!config.skipAuth) {
    const accessToken = getAccessToken()
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`)
    }
  }

  const response = await fetch(buildUrl(path), {
    ...config,
    headers,
  })

  const rawText = await response.text()
  let data: unknown = null
  if (rawText) {
    try {
      data = JSON.parse(rawText)
    } catch {
      data = rawText
    }
  }

  if (!response.ok) {
    const detail =
      typeof data === 'object' && data !== null && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : `请求失败（${response.status}）`
    throw new HttpError(response.status, detail)
  }

  return data as T
}

export function persistAuthSession(payload: AuthResponse): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, payload.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, payload.refresh_token)
}

export function clearAuthSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function readStoredTokens(): { accessToken: string | null; refreshToken: string | null } {
  return {
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
  }
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/')
  const padding = normalized.length % 4 === 0 ? '' : '='.repeat(4 - (normalized.length % 4))
  return atob(`${normalized}${padding}`)
}

/**
 * 仅用于前端快速判断 access token 是否过期。
 * 注意：该函数不做签名校验，不能替代后端鉴权。
 */
export function isAccessTokenExpired(token: string): boolean {
  try {
    const [payloadBase64] = token.split('.', 1)
    if (!payloadBase64) {
      return true
    }

    const payloadText = decodeBase64Url(payloadBase64)
    const payload = JSON.parse(payloadText) as TokenPayload
    const exp = Number(payload.exp)

    if (!Number.isFinite(exp)) {
      return true
    }

    const now = Math.floor(Date.now() / 1000)
    return exp <= now
  } catch {
    return true
  }
}
