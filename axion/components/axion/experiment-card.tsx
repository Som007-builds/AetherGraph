'use client'

import { useState } from 'react'
import { Loader2, FlaskConical, AlertTriangle, Clock, DollarSign, Database, Target } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { getExperiment, designExperiment } from '@/lib/api-client'
import type { Experiment } from '@/types/axion'

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-[#3ad389]'
  if (confidence >= 0.5) return 'text-[#ffca16]'
  return 'text-[#ff9592]'
}

interface ExperimentCardProps {
  contradictionId: string
  hasExperiment?: boolean
}

export function ExperimentCard({ contradictionId, hasExperiment }: ExperimentCardProps) {
  const [experiment, setExperiment] = useState<Experiment | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isDesigning, setIsDesigning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasFetched, setHasFetched] = useState(false)

  const fetchExperiment = async () => {
    if (hasFetched) return
    setIsLoading(true)
    try {
      const exp = await getExperiment(contradictionId)
      setExperiment(exp)
      setHasFetched(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiment')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDesign = async () => {
    setIsDesigning(true)
    setError(null)
    try {
      const exp = await designExperiment(contradictionId)
      setExperiment(exp)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to design experiment')
    } finally {
      setIsDesigning(false)
    }
  }

  // Auto-fetch if we know there's an experiment
  if (hasExperiment && !hasFetched && !isLoading) {
    fetchExperiment()
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-4 text-[#a1a4a5]">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading experiment...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-[#ff9592]/30 bg-[#ff9592]/5 p-3">
        <p className="text-sm text-[#ff9592]">{error}</p>
      </div>
    )
  }

  if (!experiment) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-[#292d30] bg-black/50 p-4">
        <div className="flex items-center gap-2 text-[#a1a4a5]">
          <FlaskConical className="h-4 w-4" />
          <span className="text-sm">No experiment designed yet</span>
        </div>
        <Button
          onClick={handleDesign}
          disabled={isDesigning}
          variant="outline"
          size="sm"
          className="border-[#70b8ff] bg-transparent text-[#70b8ff] hover:bg-[#70b8ff]/10"
        >
          {isDesigning ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Designing...</span>
            </>
          ) : (
            <span>Design Experiment</span>
          )}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 rounded-xl border border-[#292d30] bg-black p-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-[#70b8ff]" />
          <h4 className="font-medium text-[#f0f0f0]">{experiment.title}</h4>
        </div>
        <Badge
          variant="outline"
          className={`border-[#292d30] bg-transparent ${getConfidenceColor(experiment.design_confidence)}`}
        >
          {Math.round(experiment.design_confidence * 100)}% design confidence
        </Badge>
      </div>

      {/* Hypotheses */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-[#292d30] bg-[#0b0e14] p-4">
          <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#3ad389]">
            Hypothesis A
          </h5>
          <p className="text-sm text-[#a1a4a5]">{experiment.hypothesis_a}</p>
        </div>
        <div className="rounded-lg border border-[#292d30] bg-[#0b0e14] p-4">
          <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#ff9592]">
            Hypothesis B
          </h5>
          <p className="text-sm text-[#a1a4a5]">{experiment.hypothesis_b}</p>
        </div>
      </div>

      {/* Procedure */}
      <div>
        <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#6c6c6c]">
          Procedure
        </h5>
        {(() => {
          const lines = experiment.procedure.split(/\r?\n/).map(l => l.trim()).filter(Boolean)
          if (lines.length <= 1) {
            return <p className="text-sm text-[#a1a4a5] leading-relaxed">{experiment.procedure}</p>
          }
          return (
            <ol className="list-decimal pl-5 space-y-1.5 text-sm text-[#a1a4a5]">
              {lines.map((line, i) => {
                const clean = line.replace(/^\d+[\.\)]\s*/, '')
                return (
                  <li key={i} className="leading-relaxed">
                    {clean}
                  </li>
                )
              })}
            </ol>
          )
        })()}
      </div>

      {/* Metrics */}
      <div className="flex flex-wrap gap-4 text-sm">
        <div className="flex items-center gap-2 text-[#a1a4a5]">
          <Database className="h-4 w-4 text-[#9281f7]" />
          <span>{experiment.dataset}</span>
        </div>
        <div className="flex items-center gap-2 text-[#a1a4a5]">
          <Clock className="h-4 w-4 text-[#70b8ff]" />
          <span>{experiment.duration}</span>
        </div>
        <div className="flex items-center gap-2 text-[#a1a4a5]">
          <DollarSign className="h-4 w-4 text-[#3ad389]" />
          <span>{experiment.cost}</span>
        </div>
        {experiment.metric && (
          <div className="flex items-center gap-2 text-[#a1a4a5]">
            <Target className="h-4 w-4 text-[#baa7ff]" />
            <span>{experiment.metric}</span>
          </div>
        )}
      </div>

      {/* Decision Rule */}
      <div className="rounded-lg border border-[#3b9eff]/30 bg-[#3b9eff]/5 p-4">
        <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-[#3b9eff]">
          Decision Rule
        </h5>
        <p className="text-sm text-[#f0f0f0]">{experiment.decision_rule}</p>
      </div>

      {/* Caveats */}
      {experiment.caveats && experiment.caveats.length > 0 && (
        <div className="rounded-lg border border-[#ffca16]/30 bg-[#ffca16]/5 p-4">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-[#ffca16]" />
            <h5 className="text-xs font-medium uppercase tracking-wider text-[#ffca16]">
              Caveats
            </h5>
          </div>
          <ul className="list-inside list-disc space-y-1 text-sm text-[#a1a4a5]">
            {experiment.caveats.map((caveat, i) => (
              <li key={i}>{caveat}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
