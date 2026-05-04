/* Capture global Cmd+K / Ctrl+K with priority over editors. */

import { useEffect } from 'react'

export function useGlobalShortcut(handler: (e: KeyboardEvent) => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        e.stopPropagation()
        handler(e)
      }
    }
    // Capture phase to beat Monaco's own keybindings.
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [handler])
}
