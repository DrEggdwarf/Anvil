// Sprint 17-C: tests for the generic <FilterableList> extracted from PwnMode.

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FilterableList } from '../FilterableList'

const symbols = [
  { name: 'main', address: '0x401120' },
  { name: 'malloc', address: '0x401050' },
  { name: 'system', address: '0x4010a0' },
]

describe('<FilterableList>', () => {
  it('renders the empty state when no items are provided', () => {
    render(
      <FilterableList
        items={[]}
        emptyText="Nothing here"
        getFilterText={() => ''}
        renderRow={() => null}
      />
    )
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
  })

  it('renders one row per item', () => {
    render(
      <FilterableList
        items={symbols}
        emptyText="empty"
        getFilterText={s => s.name}
        renderRow={s => <span>{s.name}</span>}
      />
    )
    expect(screen.getByText('main')).toBeInTheDocument()
    expect(screen.getByText('malloc')).toBeInTheDocument()
    expect(screen.getByText('system')).toBeInTheDocument()
  })

  it('filters case-insensitively as the user types', async () => {
    const user = userEvent.setup()
    render(
      <FilterableList
        items={symbols}
        emptyText="empty"
        getFilterText={s => s.name}
        renderRow={s => <span>{s.name}</span>}
      />
    )
    const input = screen.getByPlaceholderText('Filtrer...')
    await user.type(input, 'MAL')
    expect(screen.getByText('malloc')).toBeInTheDocument()
    expect(screen.queryByText('main')).not.toBeInTheDocument()
    expect(screen.queryByText('system')).not.toBeInTheDocument()
  })

  it('caps the rendered rows when maxDisplay is set and shows the clipped count', () => {
    const many = Array.from({ length: 10 }, (_, i) => ({ id: i }))
    render(
      <FilterableList
        items={many}
        emptyText="empty"
        maxDisplay={3}
        getFilterText={x => String(x.id)}
        renderRow={x => <span>item-{x.id}</span>}
      />
    )
    expect(screen.getByText('item-0')).toBeInTheDocument()
    expect(screen.getByText('item-2')).toBeInTheDocument()
    expect(screen.queryByText('item-3')).not.toBeInTheDocument()
    expect(screen.getByText('+7 more...')).toBeInTheDocument()
  })

  it('honors a custom placeholder', () => {
    render(
      <FilterableList
        items={symbols}
        emptyText="empty"
        placeholder="Filter strings..."
        getFilterText={s => s.name}
        renderRow={s => <span>{s.name}</span>}
      />
    )
    expect(screen.getByPlaceholderText('Filter strings...')).toBeInTheDocument()
  })
})
