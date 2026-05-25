'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { Lightbulb, Sparkles, Search } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { getGaps } from '@/lib/api-client'
import type { Gap, GapsResponse } from '@/types/axion'

type SourceFilter = 'all' | 'semantic' | 'llm_synthesized'

function GapCard({ gap }: { gap: Gap }) {
  return (
    <div className="rounded-xl border border-[#292d30] bg-black p-5 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-[#9281f7]" />
          <Badge
            variant="outline"
            className={`border-[#292d30] bg-transparent ${
              gap.source === 'semantic' 
                ? 'text-[#70b8ff]' 
                : 'text-[#baa7ff]'
            }`}
          >
            {gap.source === 'semantic' ? 'Semantic' : 'LLM Synthesized'}
          </Badge>
        </div>
        {gap.confidence !== undefined && (
          <span className="text-xs text-[#6c6c6c]">
            {Math.round(gap.confidence * 100)}% confidence
          </span>
        )}
      </div>
      
      <p className="text-[#f0f0f0]">{gap.text}</p>
      
      {gap.related_claims.length > 0 && (
        <div className="pt-2">
          <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#6c6c6c]">
            Related Claims ({gap.related_claims.length})
          </h5>
          <div className="flex flex-wrap gap-2">
            {gap.related_claims.slice(0, 5).map((claimId, i) => (
              <span
                key={i}
                className="font-mono text-xs text-[#9281f7] rounded bg-[#9281f7]/10 px-2 py-1"
              >
                {claimId}
              </span>
            ))}
            {gap.related_claims.length > 5 && (
              <span className="text-xs text-[#6c6c6c]">
                +{gap.related_claims.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function GapSkeleton() {
  return (
    <div className="rounded-xl border border-[#292d30] bg-black p-5 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-5 w-5 bg-[#1b1b1b]" />
        <Skeleton className="h-5 w-24 bg-[#1b1b1b]" />
      </div>
      <Skeleton className="h-4 w-full bg-[#1b1b1b]" />
      <Skeleton className="h-4 w-4/5 bg-[#1b1b1b]" />
    </div>
  )
}

export function GapList() {
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')

  const { data, isLoading, error } = useSWR<GapsResponse>(
    ['gaps', sourceFilter],
    () => getGaps(sourceFilter === 'all' ? undefined : sourceFilter),
    { refreshInterval: 60000 }
  )

  const filterButtons: { value: SourceFilter; label: string; icon: React.ReactNode }[] = [
    { value: 'all', label: 'All', icon: <Search className="h-4 w-4" /> },
    { value: 'semantic', label: 'Semantic', icon: <Search className="h-4 w-4" /> },
    { value: 'llm_synthesized', label: 'LLM Synthesized', icon: <Sparkles className="h-4 w-4" /> },
  ]

  return (
    <div className="space-y-6">
      {/* Filter */}
      <div className="flex items-center gap-2 rounded-xl border border-[#292d30] bg-black p-2">
        {filterButtons.map((btn) => (
          <Button
            key={btn.value}
            variant="ghost"
            size="sm"
            onClick={() => setSourceFilter(btn.value)}
            className={`${
              sourceFilter === btn.value
                ? 'bg-[#1b1b1b] text-[#f0f0f0]'
                : 'text-[#6c6c6c] hover:text-[#a1a4a5]'
            }`}
          >
            {btn.icon}
            <span>{btn.label}</span>
          </Button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-[#ff9592]/30 bg-[#ff9592]/5 p-4">
          <p className="text-sm text-[#ff9592]">
            Failed to load research gaps. Is the API running?
          </p>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <GapSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-[#6c6c6c]">
              {data.total} research gap{data.total !== 1 ? 's' : ''} found
            </p>
          </div>
          <div className="space-y-4">
            {data.gaps.map((gap) => (
              <GapCard key={gap.id} gap={gap} />
            ))}
          </div>
          {data.gaps.length === 0 && (
            <div className="rounded-xl border border-[#292d30] bg-black p-8 text-center">
              <Lightbulb className="mx-auto h-8 w-8 text-[#6c6c6c]" />
              <p className="mt-3 text-[#a1a4a5]">
                No research gaps found with the current filter
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
