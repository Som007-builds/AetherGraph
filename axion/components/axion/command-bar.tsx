'use client'

import { useState, useRef, useEffect } from 'react'
import { Search, ArrowRight, Clock, Sparkles } from 'lucide-react'

interface CommandBarProps {
  onSubmit: (query: string) => void
  recentQueries?: string[]
  isLoading?: boolean
}

export function CommandBar({ onSubmit, recentQueries = [], isLoading }: CommandBarProps) {
  const [value, setValue] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [showRecent, setShowRecent] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // ⌘K keyboard shortcut
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (value.trim() && !isLoading) {
      onSubmit(value.trim())
      setValue('')
      setShowRecent(false)
      inputRef.current?.blur()
    }
  }

  function handleRecentSelect(query: string) {
    onSubmit(query)
    setValue('')
    setShowRecent(false)
    inputRef.current?.blur()
  }

  return (
    <div className="relative">
      <form onSubmit={handleSubmit} className="relative">
        <div
          className={`
            relative flex items-center rounded-xl border transition-all duration-200
            ${isFocused
              ? 'border-[rgba(59,130,246,0.3)] bg-[var(--axion-surface-2)] shadow-[0_0_20px_rgba(59,130,246,0.1)]'
              : 'border-[var(--axion-border-subtle)] bg-[var(--axion-surface-1)] hover:border-[rgba(59,130,246,0.15)]'
            }
          `}
        >
          <div className="flex items-center pl-4">
            {isLoading ? (
              <Sparkles className="h-4 w-4 text-[#3b82f6] animate-pulse" />
            ) : (
              <Search className="h-4 w-4 text-[#475569]" />
            )}
          </div>
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onFocus={() => { setIsFocused(true); setShowRecent(true) }}
            onBlur={() => { setIsFocused(false); setTimeout(() => setShowRecent(false), 200) }}
            placeholder="Ask a research question across your knowledge graph..."
            disabled={isLoading}
            className="flex-1 bg-transparent px-3 py-3 text-sm text-[#f0f6ff] placeholder:text-[#334155] focus:outline-none disabled:opacity-50"
          />
          <div className="flex items-center gap-2 pr-3">
            {!isFocused && !value && (
              <kbd className="hidden items-center gap-0.5 rounded-md border border-[var(--axion-border-subtle)] bg-[var(--axion-surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[#334155] sm:flex">
                ⌘K
              </kbd>
            )}
            {value && (
              <button
                type="submit"
                disabled={isLoading}
                className="flex h-6 w-6 items-center justify-center rounded-md bg-[#3b82f6] text-white transition-all duration-150 hover:bg-[#2563eb] disabled:opacity-50"
              >
                <ArrowRight className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Recent Queries Dropdown */}
      {showRecent && recentQueries.length > 0 && !value && (
        <div className="absolute left-0 right-0 top-full z-50 mt-2 rounded-xl border border-[var(--axion-border-subtle)] bg-[var(--axion-surface-2)] p-1 shadow-[0_8px_32px_rgba(0,0,0,0.5)] animate-fade-up">
          <div className="px-3 py-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-[#334155]">Recent</span>
          </div>
          {recentQueries.slice(0, 5).map((query, i) => (
            <button
              key={i}
              onClick={() => handleRecentSelect(query)}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-[#94a3b8] transition-colors duration-100 hover:bg-[rgba(59,130,246,0.06)] hover:text-[#f0f6ff]"
            >
              <Clock className="h-3.5 w-3.5 shrink-0 text-[#334155]" />
              <span className="truncate">{query}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
