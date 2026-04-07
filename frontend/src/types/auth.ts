export type GenderValue = 'male' | 'female' | 'unknown'

export interface UserProfile {
  id: number
  username: string
  gender: GenderValue
  age: number | null
  email: string
  registration_init_time: string | null
}

export interface RegisterRequest {
  username: string
  gender: GenderValue
  birthday: string
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  access_expires_at: string
  refresh_expires_at: string
  user: UserProfile
}

export interface UpdateUserProfileRequest {
  username?: string
  gender?: GenderValue
  birthday?: string
}
