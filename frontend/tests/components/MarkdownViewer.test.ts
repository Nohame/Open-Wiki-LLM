import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MarkdownViewer from '~/components/wiki/MarkdownViewer.vue'

describe('MarkdownViewer', () => {
  it('renders Markdown content as HTML', () => {
    const wrapper = mount(MarkdownViewer, {
      props: { content: '# Titre\n\nParagraphe de test.' },
    })
    const html = wrapper.html()
    expect(html).toContain('<h1>')
    expect(html).toContain('Titre')
    expect(html).toContain('<p>')
    expect(html).toContain('Paragraphe de test.')
  })

  it('renders empty string without crashing', () => {
    const wrapper = mount(MarkdownViewer, {
      props: { content: '' },
    })
    expect(wrapper.html()).toBeTruthy()
  })
})
