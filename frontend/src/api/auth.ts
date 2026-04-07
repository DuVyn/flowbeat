import type { AuthResponse, LoginRequest, RegisterRequest } from '@/types/auth'
import { requestJson } from '@/api/http'

export async function register(payload: RegisterRequest): Promise<AuthResponse> {
  return requestJson<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function login(payload: LoginRequest): Promise<AuthResponse> {
  return requestJson<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function logout(): Promise<{ detail: string }> {
  return requestJson<{ detail: string }>('/api/auth/logout', {
    method: 'POST',
  })
}
