import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WikiPageCard from '~/components/wiki/WikiPageCard.vue'

const page = {
  slug: 'imports--test',
  title: 'Page Test',
  type: 'concept',
  status: 'draft',
  confidence: 'medium',
  sources: [],
  updated_at: '2026-05-21',
  tags: [],
}

describe('WikiPageCard', () => {
  it('affiche le titre et le statut', () => {
    const wrapper = mount(WikiPageCard, { props: { page } })
    expect(wrapper.text()).toContain('Page Test')
    expect(wrapper.text()).toContain('draft')
  })

  it("n'affiche pas la confirmation par défaut", () => {
    const wrapper = mount(WikiPageCard, { props: { page } })
    expect(wrapper.text()).not.toContain('Supprimer ?')
  })

  it('affiche la confirmation inline au clic sur la poubelle', async () => {
    const wrapper = mount(WikiPageCard, { props: { page } })
    await wrapper.find('[data-testid="delete-btn"]').trigger('click')
    expect(wrapper.text()).toContain('Supprimer ?')
  })

  it('annuler cache la confirmation', async () => {
    const wrapper = mount(WikiPageCard, { props: { page } })
    await wrapper.find('[data-testid="delete-btn"]').trigger('click')
    await wrapper.find('[data-testid="cancel-btn"]').trigger('click')
    expect(wrapper.text()).not.toContain('Supprimer ?')
  })

  it('confirmer émet delete avec le slug', async () => {
    const wrapper = mount(WikiPageCard, { props: { page } })
    await wrapper.find('[data-testid="delete-btn"]').trigger('click')
    await wrapper.find('[data-testid="confirm-btn"]').trigger('click')
    expect(wrapper.emitted('delete')).toEqual([['imports--test']])
  })
})
