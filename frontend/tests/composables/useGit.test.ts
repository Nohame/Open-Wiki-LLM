import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()
vi.mock('~/composables/useApi', () => ({
  useApi: () => ({ get: mockGet, post: mockPost }),
}))

import type { GitStatus } from '~/types/api'

const mockStatus: GitStatus = {
  enabled: true,
  initialized: true,
  last_commit: 'abc1234 chore(wiki): init',
  dirty_files: 0,
}

describe('useGit', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockPost.mockReset()
  })

  it('fetchStatus populates status', async () => {
    mockGet.mockResolvedValue(mockStatus)
    const { useGit } = await import('~/composables/useGit')
    const { status, fetchStatus } = useGit()
    await fetchStatus()
    expect(status.value).toEqual(mockStatus)
  })

  it('fetchStatus sets error on failure', async () => {
    mockGet.mockRejectedValue(new Error('Network error'))
    const { useGit } = await import('~/composables/useGit')
    const { error, fetchStatus } = useGit()
    await fetchStatus()
    expect(error.value).toBe('Network error')
  })

  it('initRepo appelle POST /api/git/init puis fetchStatus', async () => {
    mockPost.mockResolvedValue({ status: 'initialized' })
    mockGet.mockResolvedValue(mockStatus)
    const { useGit } = await import('~/composables/useGit')
    const { status, loading, initRepo } = useGit()
    await initRepo()
    expect(mockPost).toHaveBeenCalledWith('/api/git/init', {})
    expect(mockGet).toHaveBeenCalledWith('/api/git/status')
    expect(status.value).toEqual(mockStatus)
    expect(loading.value).toBe(false)
  })

  it('pushRepo appelle POST /api/git/push puis fetchStatus', async () => {
    mockPost.mockResolvedValue({ status: 'push_triggered' })
    mockGet.mockResolvedValue(mockStatus)
    const { useGit } = await import('~/composables/useGit')
    const { pushRepo } = useGit()
    await pushRepo()
    expect(mockPost).toHaveBeenCalledWith('/api/git/push', {})
    expect(mockGet).toHaveBeenCalledWith('/api/git/status')
  })

  it("initRepo set error et remet loading à false en cas d'échec", async () => {
    mockPost.mockRejectedValue(new Error('Init failed'))
    const { useGit } = await import('~/composables/useGit')
    const { error, loading, initRepo } = useGit()
    await initRepo()
    expect(error.value).toBe('Init failed')
    expect(loading.value).toBe(false)
  })

  it("pushRepo set error et remet loading à false en cas d'échec", async () => {
    mockPost.mockRejectedValue(new Error('Push failed'))
    const { useGit } = await import('~/composables/useGit')
    const { error, loading, pushRepo } = useGit()
    await pushRepo()
    expect(error.value).toBe('Push failed')
    expect(loading.value).toBe(false)
  })
})
