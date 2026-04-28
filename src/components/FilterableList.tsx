// Sprint 17-C: generic filterable list — extracted from the SymbolsList /
// StringsList duplication that was inlined in PwnMode.tsx (Quality finding).
//
// Both lists shared the same shape: filter input + scrollable list + optional
// cap. This component owns the filter state and renders a custom row per item.

import { memo, useState, type ReactNode } from 'react'

export interface FilterableListProps<T> {
  items: T[]
  /** Returns the string the filter matches against (case-insensitive). */
  getFilterText: (item: T) => string
  /** Renders a single row. The list provides the wrapping container. */
  renderRow: (item: T, index: number) => ReactNode
  /** React key strategy. Defaults to index — supply when items have stable IDs. */
  getKey?: (item: T, index: number) => string | number
  placeholder?: string
  /** Shown when `items` is empty (before any filter is applied). */
  emptyText: string
  /** Cap the rendered rows; a "+N more..." footer surfaces what was clipped. */
  maxDisplay?: number
  /** Optional CSS class on the outer wrapper for component-specific styling. */
  className?: string
}

function FilterableListInner<T>({
  items,
  getFilterText,
  renderRow,
  getKey,
  placeholder = 'Filtrer...',
  emptyText,
  maxDisplay,
  className = 'anvil-pwn-symbols',
}: FilterableListProps<T>) {
  const [filter, setFilter] = useState('')

  if (items.length === 0) return <div className="anvil-pwn-empty">{emptyText}</div>

  const needle = filter.toLowerCase()
  const filtered = needle
    ? items.filter(item => getFilterText(item).toLowerCase().includes(needle))
    : items

  const visible = maxDisplay !== undefined ? filtered.slice(0, maxDisplay) : filtered
  const clipped = maxDisplay !== undefined ? Math.max(0, filtered.length - maxDisplay) : 0

  return (
    <div className={className}>
      <input
        className="anvil-pwn-filter"
        placeholder={placeholder}
        value={filter}
        onChange={e => setFilter(e.target.value)}
      />
      <div className="anvil-pwn-symbol-list">
        {visible.map((item, i) => (
          <div key={getKey ? getKey(item, i) : i} className="anvil-pwn-symbol-row">
            {renderRow(item, i)}
          </div>
        ))}
        {clipped > 0 && <div className="anvil-pwn-empty">+{clipped} more...</div>}
      </div>
    </div>
  )
}

// `memo` cast keeps the generic signature; React.memo loses the parameter.
export const FilterableList = memo(FilterableListInner) as typeof FilterableListInner
