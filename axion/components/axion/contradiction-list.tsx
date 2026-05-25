'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { ChevronDown, ChevronRight, AlertTriangle, FileText } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ExperimentCard } from './experiment-card'
import { getContradictions } from '@/lib/api-client'
import type { Contradiction, ContradictionsResponse } from '@/types/axion'

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-[#3ad389]'
  if (confidence >= 0.5) return 'text-[#ffca16]'
  return 'text-[#ff9592]'
}

function getConfidenceBg(confidence: number): string {
  if (confidence >= 0.8) return 'bg-[#3ad389]/10 border-[#3ad389]/30'
  if (confidence >= 0.5) return 'bg-[#ffca16]/10 border-[#ffca16]/30'
  return 'bg-[#ff9592]/10 border-[#ff9592]/30'
}

function ContradictionCard({ contradiction }: { contradiction: Contradiction }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="rounded-xl border border-[#292d30] bg-black">
        <CollapsibleTrigger className="flex w-full items-start gap-4 p-5 text-left hover:bg-[#0b0e14]">
          <div className="mt-1">
            {isOpen ? (
              <ChevronDown className="h-4 w-4 text-[#6c6c6c]" />
            ) : (
              <ChevronRight className="h-4 w-4 text-[#6c6c6c]" />
            )}
          </div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-4 w-4 text-[#ff9592]" />
              <Badge
                variant="outline"
                className={`border ${getConfidenceBg(contradiction.confidence)} ${getConfidenceColor(contradiction.confidence)}`}
              >
                {Math.round(contradiction.confidence * 100)}%
              </Badge>
              {contradiction.has_experiment && (
                <Badge
                  variant="outline"
                  className="border-[#70b8ff]/30 bg-[#70b8ff]/10 text-[#70b8ff]"
                >
                  Has experiment
                </Badge>
              )}
            </div>
            <p className="text-sm text-[#a1a4a5] line-clamp-2">
              {contradiction.explanation}
            </p>
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="border-t border-[#292d30] p-5 space-y-4">
            {/* Claims side by side */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-[#292d30] bg-[#0b0e14] p-4">
                <div className="mb-2 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-[#baa7ff]" />
                  <span className="font-mono text-xs text-[#9281f7]">
                    {contradiction.paper_a}
                  </span>
                </div>
                <p className="text-sm text-[#f0f0f0]">{contradiction.claim_a.text}</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-[#6c6c6c]">
                  <span>{contradiction.claim_a.section}</span>
                  <span className="text-[#292d30]">|</span>
                  <span className={getConfidenceColor(contradiction.claim_a.confidence)}>
                    {Math.round(contradiction.claim_a.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
              <div className="rounded-lg border border-[#292d30] bg-[#0b0e14] p-4">
                <div className="mb-2 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-[#baa7ff]" />
                  <span className="font-mono text-xs text-[#9281f7]">
                    {contradiction.paper_b}
                  </span>
                </div>
                <p className="text-sm text-[#f0f0f0]">{contradiction.claim_b.text}</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-[#6c6c6c]">
                  <span>{contradiction.claim_b.section}</span>
                  <span className="text-[#292d30]">|</span>
                  <span className={getConfidenceColor(contradiction.claim_b.confidence)}>
                    {Math.round(contradiction.claim_b.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
            </div>

            {/* Full explanation */}
            <div>
              <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#6c6c6c]">
                Explanation
              </h5>
              <p className="text-sm text-[#a1a4a5]">{contradiction.explanation}</p>
            </div>

            {/* Experiment */}
            <div className="pt-2">
              <ExperimentCard
                contradictionId={contradiction.id}
                hasExperiment={contradiction.has_experiment}
              />
            </div>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

function ContradictionSkeleton() {
  return (
    <div className="rounded-xl border border-[#292d30] bg-black p-5 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-5 w-5 bg-[#1b1b1b]" />
        <Skeleton className="h-5 w-16 bg-[#1b1b1b]" />
      </div>
      <Skeleton className="h-4 w-full bg-[#1b1b1b]" />
      <Skeleton className="h-4 w-3/4 bg-[#1b1b1b]" />
    </div>
  )
}

export function ContradictionList() {
  const [minConfidence, setMinConfidence] = useState(0)

  const { data, isLoading, error } = useSWR<ContradictionsResponse>(
    ['contradictions', minConfidence],
    () => getContradictions(minConfidence / 100),
    { refreshInterval: 60000 }
  )

  return (
    <div className="space-y-6">
      {/* Filter */}
      <div className="flex items-center gap-6 rounded-xl border border-[#292d30] bg-black p-4">
        <div className="flex items-center gap-2 text-sm text-[#a1a4a5]">
          <span>Min confidence:</span>
          <span className="font-mono text-[#f0f0f0]">{minConfidence}%</span>
        </div>
        <Slider
          value={[minConfidence]}
          onValueChange={([value]) => setMinConfidence(value)}
          min={0}
          max={100}
          step={5}
          className="flex-1"
        />
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-[#ff9592]/30 bg-[#ff9592]/5 p-4">
          <p className="text-sm text-[#ff9592]">
            Failed to load contradictions. Is the API running?
          </p>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <ContradictionSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-[#6c6c6c]">
              {data.total} contradiction{data.total !== 1 ? 's' : ''} found
            </p>
          </div>
          <div className="space-y-4">
            {data.contradictions.map((c) => (
              <ContradictionCard key={c.id} contradiction={c} />
            ))}
          </div>
          {data.contradictions.length === 0 && (
            <div className="rounded-xl border border-[#292d30] bg-black p-8 text-center">
              <AlertTriangle className="mx-auto h-8 w-8 text-[#6c6c6c]" />
              <p className="mt-3 text-[#a1a4a5]">
                No contradictions found with confidence above {minConfidence}%
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
