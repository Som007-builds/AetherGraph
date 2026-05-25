'use client'

import { useState } from 'react'
import { Search, Loader2, Calendar, FileText, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Slider } from '@/components/ui/slider'
import { getEvolution, getDisputes } from '@/lib/api-client'
import type { TemporalEvolution, DisputeTimeline, YearlyPosition, Dispute } from '@/types/axion'

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-[#3ad389]'
  if (confidence >= 0.5) return 'bg-[#ffca16]'
  return 'bg-[#ff9592]'
}

function YearlyPositionCard({ position }: { position: YearlyPosition }) {
  return (
    <div className="relative flex gap-4">
      {/* Year marker */}
      <div className="flex flex-col items-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#292d30] bg-black">
          <span className="text-sm font-medium text-[#f0f0f0]">{position.year}</span>
        </div>
        <div className="flex-1 w-px bg-[#292d30]" />
      </div>
      
      {/* Content */}
      <div className="flex-1 pb-6">
        <div className="rounded-xl border border-[#292d30] bg-black p-4 space-y-3">
          <div className="flex items-center gap-3">
            <div className={`h-2 w-2 rounded-full ${getConfidenceColor(position.confidence)}`} />
            <span className="text-xs text-[#6c6c6c]">
              {Math.round(position.confidence * 100)}% confidence
            </span>
          </div>
          <p className="text-sm text-[#f0f0f0]">{position.position}</p>
          {position.key_papers.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {position.key_papers.map((paper, i) => (
                <Badge
                  key={i}
                  variant="outline"
                  className="border-[#292d30] bg-transparent font-mono text-xs text-[#9281f7]"
                >
                  <FileText className="mr-1 h-3 w-3" />
                  {paper}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function DisputeCard({ dispute }: { dispute: Dispute }) {
  const duration = dispute.end_year 
    ? `${dispute.start_year} - ${dispute.end_year}`
    : `${dispute.start_year} - ongoing`

  return (
    <div className="rounded-xl border border-[#292d30] bg-black p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-[#70b8ff]" />
          <span className="text-sm text-[#a1a4a5]">{duration}</span>
        </div>
        <Badge
          variant="outline"
          className={`${
            dispute.resolved
              ? 'border-[#3ad389]/30 bg-[#3ad389]/10 text-[#3ad389]'
              : 'border-[#ffca16]/30 bg-[#ffca16]/10 text-[#ffca16]'
          }`}
        >
          {dispute.resolved ? (
            <>
              <CheckCircle className="mr-1 h-3 w-3" />
              Resolved
            </>
          ) : (
            <>
              <XCircle className="mr-1 h-3 w-3" />
              Ongoing
            </>
          )}
        </Badge>
      </div>
      
      <p className="text-[#f0f0f0]">{dispute.topic}</p>
      
      {dispute.resolution && (
        <div className="rounded-lg border border-[#3ad389]/30 bg-[#3ad389]/5 p-3">
          <p className="text-sm text-[#3ad389]">{dispute.resolution}</p>
        </div>
      )}
      
      {dispute.key_claims.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {dispute.key_claims.map((claimId, i) => (
            <span
              key={i}
              className="font-mono text-xs text-[#baa7ff] rounded bg-[#baa7ff]/10 px-2 py-1"
            >
              {claimId}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function TimelineView() {
  const [topic, setTopic] = useState('')
  const [yearRange, setYearRange] = useState([2020, 2026])
  const [isLoading, setIsLoading] = useState(false)
  const [evolution, setEvolution] = useState<TemporalEvolution | null>(null)
  const [disputes, setDisputes] = useState<DisputeTimeline | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    if (!topic.trim()) return
    
    setIsLoading(true)
    setError(null)
    
    try {
      const [evoResult, disputeResult] = await Promise.all([
        getEvolution(topic.trim(), yearRange[0], yearRange[1]),
        getDisputes(topic.trim()),
      ])
      setEvolution(evoResult)
      setDisputes(disputeResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline data')
      setEvolution(null)
      setDisputes(null)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Search controls */}
      <div className="space-y-4 rounded-xl border border-[#292d30] bg-black p-5">
        <div className="flex gap-4">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter a research topic... e.g., transformer scaling laws"
            className="flex-1 rounded-lg border border-[#292d30] bg-black px-4 py-2 text-[#f0f0f0] placeholder:text-[#6c6c6c] focus:border-[#3b9eff] focus:outline-none focus:ring-1 focus:ring-[#3b9eff]/50"
          />
          <Button
            onClick={handleSearch}
            disabled={!topic.trim() || isLoading}
            className="border border-[#3b9eff] bg-transparent text-white hover:bg-[#3b9eff]/10"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            <span>Search</span>
          </Button>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-sm text-[#a1a4a5]">
            <span>Year range:</span>
            <span className="font-mono text-[#f0f0f0]">
              {yearRange[0]} - {yearRange[1]}
            </span>
          </div>
          <Slider
            value={yearRange}
            onValueChange={setYearRange}
            min={2015}
            max={2026}
            step={1}
            className="flex-1"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-[#ff9592]/30 bg-[#ff9592]/5 p-4">
          <p className="text-sm text-[#ff9592]">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="rounded-xl border border-[#292d30] bg-black p-6">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-[#3b9eff]" />
            <span className="text-[#a1a4a5]">
              Analyzing temporal evolution for &quot;{topic}&quot;...
            </span>
          </div>
        </div>
      )}

      {/* Results */}
      {evolution && !isLoading && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Evolution timeline */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-[#f0f0f0]">
              Evolution of &quot;{evolution.topic}&quot;
            </h3>
            
            {/* Narrative */}
            <div className="rounded-xl border border-[#292d30] bg-black p-5">
              <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#6c6c6c]">
                Narrative Summary
              </h4>
              <p className="text-sm text-[#a1a4a5]">{evolution.narrative}</p>
            </div>

            {/* Current status */}
            <div className="rounded-xl border border-[#3b9eff]/30 bg-[#3b9eff]/5 p-5">
              <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#3b9eff]">
                Current Status
              </h4>
              <p className="text-sm text-[#f0f0f0]">{evolution.current_status}</p>
            </div>

            {/* Timeline */}
            <div className="pt-4">
              {evolution.yearly_positions.map((pos) => (
                <YearlyPositionCard key={pos.year} position={pos} />
              ))}
            </div>
          </div>

          {/* Disputes */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-[#f0f0f0]">
              Scientific Disputes
            </h3>
            
            {disputes && disputes.disputes.length > 0 ? (
              <div className="space-y-4">
                {disputes.disputes.map((dispute) => (
                  <DisputeCard key={dispute.id} dispute={dispute} />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-[#292d30] bg-black p-8 text-center">
                <CheckCircle className="mx-auto h-8 w-8 text-[#3ad389]" />
                <p className="mt-3 text-[#a1a4a5]">
                  No major scientific disputes found for this topic
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!evolution && !isLoading && !error && (
        <div className="rounded-xl border border-[#292d30] bg-black p-12 text-center">
          <Calendar className="mx-auto h-12 w-12 text-[#6c6c6c]" />
          <h3 className="mt-4 text-lg font-medium text-[#f0f0f0]">
            Explore Scientific Evolution
          </h3>
          <p className="mt-2 text-sm text-[#a1a4a5]">
            Enter a research topic to see how scientific consensus has evolved over time
          </p>
        </div>
      )}
    </div>
  )
}
