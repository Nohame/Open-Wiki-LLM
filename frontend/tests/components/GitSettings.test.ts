import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import type { GitConfig, GitStatus } from '~/types/api'

vi.mock('~/composables/useGit', () => ({
  useGit: vi.fn(),
}))

import { useGit } from '~/composables/useGit'
import GitSettings from '~/components/settings/GitSettings.vue'

const defaultConfig: GitConfig = {
  enabled: false,
  auto_push: false,
  remote_url: '',
  branch: 'main',
}

function mockGit(overrides: {
  status?: GitStatus | null
  loading?: boolean
  error?: string | null
} = {}) {
  vi.mocked(useGit).mockReturnValue({
    status: ref(overrides.status ?? null),
    loading: ref(overrides.loading ?? false),
    error: ref(overrides.error ?? null),
    fetchStatus: vi.fn(),
    initRepo: vi.fn(),
    pushRepo: vi.fn(),
  })
}

describe('GitSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('état 1: toggle off — fieldset disabled, pas de bouton Init', () => {
    mockGit()
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: false } },
    })
    const fieldset = wrapper.find('fieldset')
    expect(fieldset.exists()).toBe(true)
    expect((fieldset.element as HTMLFieldSetElement).disabled).toBe(true)
    expect(wrapper.text()).not.toContain('Initialiser')
    expect(wrapper.text()).not.toContain('Push')
  })

  it('état 2: activé non initialisé — bouton Init visible, pas de badge statut', () => {
    mockGit({
      status: { enabled: true, initialized: false, last_commit: null, dirty_files: 0 },
    })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('Initialiser le dépôt git')
    expect(wrapper.text()).not.toContain('Push ↑')
    expect(wrapper.text()).not.toContain('Initialisé')
  })

  it('état 3: initialisé — badge statut, bouton Push, pas de bouton Init', () => {
    mockGit({
      status: {
        enabled: true,
        initialized: true,
        last_commit: 'abc1234 feat(wiki): ingest test',
        dirty_files: 2,
      },
    })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('Initialisé')
    expect(wrapper.text()).toContain('2 fichiers modifiés')
    expect(wrapper.text()).toContain('Push ↑')
    expect(wrapper.text()).not.toContain('Initialiser')
  })

  it('état 3: affiche le hash du dernier commit', () => {
    mockGit({
      status: {
        enabled: true,
        initialized: true,
        last_commit: 'abc1234 feat(wiki): ingest test',
        dirty_files: 0,
      },
    })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('abc1234')
  })

  it('clic toggle émet update:modelValue avec enabled inversé', async () => {
    mockGit()
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: false } },
    })
    await wrapper.find('button').trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect((emitted![0][0] as GitConfig).enabled).toBe(true)
  })

  it("affiche l'erreur en rouge si error est renseigné", () => {
    mockGit({ error: 'Erreur réseau' })
    const wrapper = mount(GitSettings, {
      props: { modelValue: { ...defaultConfig, enabled: true } },
    })
    expect(wrapper.text()).toContain('Erreur réseau')
  })
})
