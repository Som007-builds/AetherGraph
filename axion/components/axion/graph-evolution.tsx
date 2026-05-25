'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { TrendingUp, TrendingDown, RefreshCw, Loader2, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { getConfidenceDistribution, getMostChanged, recalculateConfidence } from '@/lib/api-client'
import type { ConfidenceDistribution, ChangedClaim } from '@/types/axion'

function ConfidenceBar({ 
  label, 
  count, 
  total, 
  color 
}: { 
  label: string
  count: number
  total: number
  color: string 
}) {
  const percentage = total > 0 ? (count / total) * 100 : 0
  
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-[#a1a4a5]">{label}</span>
        <span className="font-mono text-[#f0f0f0]">
          {count} ({percentage.toFixed(1)}%)
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-[#1b1b1b]">
        <div
          className={`h-2 rounded-full ${color} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

function ChangedClaimCard({ claim }: { claim: ChangedClaim }) {
  const isPositive = claim.delta > 0
  
  return (
    <div className="rounded-lg border border-[#292d30] bg-black p-4 space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          {isPositive ? (
            <TrendingUp className="h-4 w-4 text-[#3ad389]" />
          ) : (
            <TrendingDown className="h-4 w-4 text-[#ff9592]" />
          )}
          <span
            className={`font-mono text-sm ${isPositive ? 'text-[#3ad389]' : 'text-[#ff9592]'}`}
          >
            {isPositive ? '+' : ''}{(claim.delta * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#6c6c6c]">
          <span>{Math.round(claim.base_confidence * 100)}%</span>
          <span>→</span>
          <span className="text-[#f0f0f0]">{Math.round(claim.current_confidence * 100)}%</span>
        </div>
      </div>
      <p className="text-sm text-[#a1a4a5] line-clamp-2">{claim.claim_text}</p>
      <Badge
        variant="outline"
        className="border-[#292d30] bg-transparent text-xs text-[#6c6c6c]"
      >
        {claim.reason}
      </Badge>
    </div>
  )
}

export function GraphEvolution() {
  const [isRecalculating, setIsRecalculating] = useState(false)

  const { 
    data: distribution, 
    isLoading: distLoading, 
    error: distError,
    mutate: mutateDistribution,
  } = useSWR<ConfidenceDistribution>(
    'confidence-distribution',
    getConfidenceDistribution,
    { refreshInterval: 60000 }
  )

  const { 
    data: changedClaims, 
    isLoading: claimsLoading, 
    error: claimsError,
    mutate: mutateClaims,
  } = useSWR<ChangedClaim[]>(
    'most-changed',
    () => getMostChanged(10),
    { refreshInterval: 60000 }
  )

  const handleRecalculate = async () => {
    setIsRecalculating(true)
    try {
      await recalculateConfidence()
      // Refresh both datasets
      await Promise.all([mutateDistribution(), mutateClaims()])
    } catch (error) {
      console.error('Failed to recalculate:', error)
    } finally {
      setIsRecalculating(false)
    }
  }

  const isLoading = distLoading || claimsLoading
  const hasError = distError || claimsError

  return (
    <div className="space-y-6">
      {/* Header with recalculate button */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-[#f0f0f0]">
          Confidence Analysis
        </h3>
        <Button
          onClick={handleRecalculate}
          disabled={isRecalculating}
          variant="outline"
          size="sm"
          className="border-[#292d30] bg-transparent text-[#a1a4a5] hover:border-[#3b9eff] hover:text-[#f0f0f0]"
        >
          {isRecalculating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          <span>Recalculate</span>
        </Button>
      </div>

      {/* Error state */}
      {hasError && (
        <div className="rounded-xl border border-[#ff9592]/30 bg-[#ff9592]/5 p-4">
          <p className="text-sm text-[#ff9592]">
            Failed to load confidence data. Is the API running?
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Confidence Distribution */}
        <div className="rounded-xl border border-[#292d30] bg-black p-5 space-y-6">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-[#70b8ff]" />
            <h4 className="font-medium text-[#f0f0f0]">Confidence Distribution</h4>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-full bg-[#1b1b1b]" />
                  <Skeleton className="h-2 w-full bg-[#1b1b1b]" />
                </div>
              ))}
            </div>
          ) : distribution ? (
            <>
              <div className="space-y-4">
                <ConfidenceBar
                  label="High (>80%)"
                  count={distribution.high}
                  total={distribution.total}
                  color="bg-[#3ad389]"
                />
                <ConfidenceBar
                  label="Medium (50-80%)"
                  count={distribution.medium}
                  total={distribution.total}
                  color="bg-[#ffca16]"
                />
                <ConfidenceBar
                  label="Low (<50%)"
                  count={distribution.low}
                  total={distribution.total}
                  color="bg-[#ff9592]"
                />
              </div>

              <div className="flex items-center justify-between border-t border-[#292d30] pt-4 text-sm">
                <span className="text-[#6c6c6c]">Total claims</span>
                <span className="font-mono text-[#f0f0f0]">{distribution.total}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-[#6c6c6c]">Average confidence</span>
                <span className="font-mono text-[#f0f0f0]">
                  {Math.round(distribution.average * 100)}%
                </span>
              </div>
            </>
          ) : null}
        </div>

        {/* Most Changed Claims */}
        <div className="rounded-xl border border-[#292d30] bg-black p-5 space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-[#3ad389]" />
            <h4 className="font-medium text-[#f0f0f0]">Most Changed Claims</h4>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20 w-full bg-[#1b1b1b]" />
              ))}
            </div>
          ) : changedClaims && changedClaims.length > 0 ? (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {changedClaims.map((claim) => (
                <ChangedClaimCard key={claim.claim_id} claim={claim} />
              ))}
            </div>
          ) : (
            <div className="py-8 text-center">
              <TrendingUp className="mx-auto h-8 w-8 text-[#6c6c6c]" />
              <p className="mt-3 text-sm text-[#a1a4a5]">
                No significant confidence changes detected
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
