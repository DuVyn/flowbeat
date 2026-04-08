import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getSongStream } from '@/api/song'
import type { Track } from '@/types/music'

const DEFAULT_VOLUME = 80

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

export const usePlayerStore = defineStore('player', () => {
  const playlist = ref<Track[]>([])
  const currentIndex = ref(-1)
  const isPlaying = ref(false)
  const isLoading = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(DEFAULT_VOLUME)
  const isMuted = ref(false)
  const errorMessage = ref('')

  let audio: HTMLAudioElement | null = null

  const currentTrack = computed<Track | null>(() => {
    if (currentIndex.value < 0) {
      return null
    }
    return playlist.value[currentIndex.value] ?? null
  })

  const progressPercent = computed(() => {
    if (duration.value <= 0) {
      return 0
    }
    return clamp((currentTime.value / duration.value) * 100, 0, 100)
  })

  const effectiveVolume = computed(() => (isMuted.value ? 0 : volume.value))

  function ensureAudio(): HTMLAudioElement {
    if (audio) {
      return audio
    }

    audio = new Audio()
    audio.preload = 'metadata'
    audio.volume = volume.value / 100

    audio.addEventListener('timeupdate', () => {
      currentTime.value = audio?.currentTime ?? 0
    })
    audio.addEventListener('loadedmetadata', () => {
      const loadedDuration = audio?.duration
      duration.value = Number.isFinite(loadedDuration) ? (loadedDuration ?? 0) : 0
    })
    audio.addEventListener('play', () => {
      isPlaying.value = true
    })
    audio.addEventListener('pause', () => {
      isPlaying.value = false
    })
    audio.addEventListener('ended', () => {
      void nextTrack()
    })
    audio.addEventListener('error', () => {
      errorMessage.value = '音频播放失败，请稍后重试'
      isLoading.value = false
    })

    return audio
  }

  function setPlaylist(tracks: Track[], activeTrackId: number): void {
    playlist.value = tracks
    const foundIndex = tracks.findIndex((item) => item.id === activeTrackId)
    currentIndex.value = foundIndex >= 0 ? foundIndex : 0
  }

  async function loadAndPlay(track: Track): Promise<void> {
    const player = ensureAudio()
    isLoading.value = true
    errorMessage.value = ''

    try {
      const streamInfo = await getSongStream(track.id)
      if (player.src !== streamInfo.streamUrl) {
        player.src = streamInfo.streamUrl
      }

      duration.value = track.durationMs > 0 ? track.durationMs / 1000 : 0
      currentTime.value = 0
      await player.play()
    } catch (error) {
      // 浏览器在快速切歌时可能主动中断前一个 play Promise，此类中断可忽略。
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
      errorMessage.value = error instanceof Error ? error.message : '播放失败，请稍后重试'
      isPlaying.value = false
    } finally {
      isLoading.value = false
    }
  }

  async function playTrack(track: Track, tracks?: Track[]): Promise<void> {
    if (tracks && tracks.length > 0) {
      setPlaylist(tracks, track.id)
    } else {
      const existingIndex = playlist.value.findIndex((item) => item.id === track.id)
      if (existingIndex >= 0) {
        currentIndex.value = existingIndex
      } else {
        playlist.value = [...playlist.value, track]
        currentIndex.value = playlist.value.length - 1
      }
    }
    await loadAndPlay(track)
  }

  async function togglePlayPause(): Promise<void> {
    const player = ensureAudio()
    if (!currentTrack.value) {
      return
    }
    if (isPlaying.value) {
      player.pause()
      return
    }
    if (!player.src) {
      await loadAndPlay(currentTrack.value)
      return
    }
    try {
      await player.play()
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
      errorMessage.value = error instanceof Error ? error.message : '播放失败，请稍后重试'
    }
  }

  async function nextTrack(): Promise<void> {
    if (playlist.value.length === 0) {
      return
    }
    const nextIndex = (currentIndex.value + 1) % playlist.value.length
    currentIndex.value = nextIndex
    const next = playlist.value[nextIndex]
    if (next) {
      await loadAndPlay(next)
    }
  }

  async function prevTrack(): Promise<void> {
    if (playlist.value.length === 0) {
      return
    }
    const prevIndex = currentIndex.value <= 0 ? playlist.value.length - 1 : currentIndex.value - 1
    currentIndex.value = prevIndex
    const prev = playlist.value[prevIndex]
    if (prev) {
      await loadAndPlay(prev)
    }
  }

  function seekToPercent(percent: number): void {
    const player = ensureAudio()
    const targetPercent = clamp(percent, 0, 100)
    const targetTime = (targetPercent / 100) * (duration.value || 0)
    player.currentTime = targetTime
    currentTime.value = targetTime
  }

  function setVolume(nextVolume: number): void {
    const normalized = clamp(nextVolume, 0, 100)
    volume.value = normalized
    const player = ensureAudio()
    player.volume = normalized / 100
    if (normalized > 0 && isMuted.value) {
      isMuted.value = false
      player.muted = false
    }
  }

  function toggleMute(): void {
    isMuted.value = !isMuted.value
    ensureAudio().muted = isMuted.value
  }

  return {
    currentTrack,
    isPlaying,
    isLoading,
    currentTime,
    duration,
    progressPercent,
    volume,
    effectiveVolume,
    isMuted,
    errorMessage,
    playTrack,
    togglePlayPause,
    prevTrack,
    nextTrack,
    seekToPercent,
    setVolume,
    toggleMute,
  }
})
