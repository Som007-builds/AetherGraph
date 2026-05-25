'use client'

import { useState, useEffect } from 'react'
import {
  Search,
  ChevronDown,
  ChevronRight,
  Loader2,
  BookOpen,
  Brain,
  CheckCircle2,
  Swords,
  HelpCircle,
  FlaskConical,
  ExternalLink,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Plus,
  Trash2,
  History,
  MessageSquare,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { runQuery } from '@/lib/api-client'
import type { CoordinatorOutput, ReflectionStep } from '@/types/axion'
import ReactMarkdown from 'react-markdown'
import { Skeleton } from '@/components/ui/skeleton'

// ─── Raw report JSON type from the coordinator ──────────────────────────────

interface RawReport {
  consensus?: { finding: string; citations?: string[] }[]
  disputed?: {
    topic: string
    position_a: { claim: string; paper: string } | string
    position_b: { claim: string; paper: string } | string
  }[]
  missing?: string[]
  recommended_experiments?: string[]
  confidence_in_answer?: string
  confidence_reason?: string
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getConfidenceConfig(confidence: number) {
  if (confidence >= 0.8)
    return {
      color: 'text-[#3ad389]',
      bg: 'bg-[#3ad389]/8',
      border: 'border-[#3ad389]/20',
      icon: ShieldCheck,
      label: 'High Confidence',
    }
  if (confidence >= 0.5)
    return {
      color: 'text-[#ffca16]',
      bg: 'bg-[#ffca16]/8',
      border: 'border-[#ffca16]/20',
      icon: ShieldAlert,
      label: 'Medium Confidence',
    }
  return {
    color: 'text-[#ff9592]',
    bg: 'bg-[#ff9592]/8',
    border: 'border-[#ff9592]/20',
    icon: ShieldQuestion,
    label: 'Low Confidence',
  }
}

function parseRaw(rawStr: string): RawReport {
  try {
    return JSON.parse(rawStr)
  } catch {
    return {}
  }
}

function arxivUrl(id: string): string {
  const clean = id.replace(/[\[\]]/g, '').trim()
  return `https://arxiv.org/abs/${clean}`
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function ReflectionLog({ steps }: { steps: ReflectionStep[] }) {
  const [isOpen, setIsOpen] = useState(false)

  if (steps.length === 0) return null

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 py-2 text-sm text-[#a1a4a5] hover:text-[#f0f0f0] transition-colors">
        {isOpen ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        <Brain className="h-4 w-4 text-[#9281f7]" />
        <span>Reasoning trace ({steps.length} steps)</span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-2 space-y-3 border-l-2 border-[#9281f7]/30 pl-4">
          {steps.map((step, i) => (
            <div key={i} className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#9281f7]/15 font-mono text-[10px] text-[#9281f7]">
                  {step.step}
                </span>
                <span className="text-xs text-[#6c6c6c]">{step.action}</span>
              </div>
              <p className="text-sm text-[#a1a4a5] leading-relaxed">{step.observation}</p>
              {step.reasoning && (
                <p className="text-xs text-[#6c6c6c] italic">{step.reasoning}</p>
              )}
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function PlanSteps({ plan }: { plan: string[] }) {
  const [isOpen, setIsOpen] = useState(false)

  if (plan.length === 0) return null

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 py-2 text-sm text-[#a1a4a5] hover:text-[#f0f0f0] transition-colors">
        {isOpen ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        <span>Execution plan ({plan.length} sub-queries)</span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-2 space-y-2 border-l-2 border-[#3b9eff]/30 pl-4">
          {plan.map((step, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="mt-0.5 inline-flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-[#3b9eff]/15 font-mono text-[10px] text-[#3b9eff]">
                {i + 1}
              </span>
              <span className="text-sm text-[#a1a4a5]">{step}</span>
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function CitationChip({ id }: { id: string }) {
  const clean = id.replace(/[\[\]]/g, '').trim()
  return (
    <a
      href={arxivUrl(clean)}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 rounded-md border border-[#3b9eff]/20 bg-[#3b9eff]/8 px-1.5 py-0.5 font-mono text-[11px] text-[#70b8ff] transition-colors hover:bg-[#3b9eff]/15 hover:text-[#3b9eff]"
    >
      {clean}
      <ExternalLink className="h-2.5 w-2.5" />
    </a>
  )
}

function SectionHeader({
  icon: Icon,
  title,
  count,
  color,
}: {
  icon: React.ElementType
  title: string
  count?: number
  color: string
}) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${color}`}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <h4 className="font-medium text-[#f0f0f0]">{title}</h4>
      {count !== undefined && count > 0 && (
        <span className="font-mono text-xs text-[#6c6c6c]">{count}</span>
      )}
    </div>
  )
}

// ─── Report sections ─────────────────────────────────────────────────────────

function ConsensusSection({ items }: { items: RawReport['consensus'] }) {
  if (!items || items.length === 0) return null

  return (
    <div className="rounded-xl border border-[#292d30] bg-[#0a0f0a]/50 p-5">
      <SectionHeader
        icon={CheckCircle2}
        title="Consensus"
        count={items.length}
        color="bg-[#3ad389]/10 text-[#3ad389]"
      />
      <div className="space-y-3">
        {items.map((item, i) => (
          <div
            key={i}
            className="flex gap-3 rounded-lg border border-[#3ad389]/10 bg-[#3ad389]/[0.03] p-3"
          >
            <div className="mt-1 flex-shrink-0">
              <div className="h-1.5 w-1.5 rounded-full bg-[#3ad389]" />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm text-[#d0d0d0] leading-relaxed">
                {item.finding}
              </p>
              {item.citations && item.citations.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {item.citations.map((c, j) => (
                    <CitationChip key={j} id={c} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function DisputesSection({ items }: { items: RawReport['disputed'] }) {
  if (!items || items.length === 0) return null

  return (
    <div className="rounded-xl border border-[#292d30] bg-[#150a0a]/50 p-5">
      <SectionHeader
        icon={Swords}
        title="Disputes"
        count={items.length}
        color="bg-[#ff9592]/10 text-[#ff9592]"
      />
      <div className="space-y-4">
        {items.map((d, i) => {
          const pa = typeof d.position_a === 'string'
            ? { claim: d.position_a, paper: '?' }
            : d.position_a
          const pb = typeof d.position_b === 'string'
            ? { claim: d.position_b, paper: '?' }
            : d.position_b

          return (
            <div
              key={i}
              className="rounded-lg border border-[#ff9592]/10 bg-[#ff9592]/[0.03] p-4 space-y-3"
            >
              <p className="text-sm font-medium text-[#f0f0f0]">{d.topic}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {/* Position A */}
                <div className="rounded-md border border-[#292d30] bg-black/40 p-3 space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className="inline-block h-2 w-2 rounded-full bg-[#3b9eff]" />
                    <span className="text-[10px] font-medium uppercase tracking-wider text-[#6c6c6c]">
                      Position A
                    </span>
                  </div>
                  <p className="text-xs text-[#a1a4a5] leading-relaxed">
                    {pa.claim}
                  </p>
                  {pa.paper && pa.paper !== '?' && (
                    <CitationChip id={pa.paper} />
                  )}
                </div>
                {/* Position B */}
                <div className="rounded-md border border-[#292d30] bg-black/40 p-3 space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className="inline-block h-2 w-2 rounded-full bg-[#ff9592]" />
                    <span className="text-[10px] font-medium uppercase tracking-wider text-[#6c6c6c]">
                      Position B
                    </span>
                  </div>
                  <p className="text-xs text-[#a1a4a5] leading-relaxed">
                    {pb.claim}
                  </p>
                  {pb.paper && pb.paper !== '?' && (
                    <CitationChip id={pb.paper} />
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function GapsSection({ items }: { items: string[] }) {
  if (!items || items.length === 0) return null

  return (
    <div className="rounded-xl border border-[#292d30] bg-[#0f0a15]/50 p-5">
      <SectionHeader
        icon={HelpCircle}
        title="Research Gaps"
        count={items.length}
        color="bg-[#9281f7]/10 text-[#9281f7]"
      />
      <div className="space-y-2">
        {items.map((gap, i) => (
          <div
            key={i}
            className="flex gap-3 rounded-lg border border-[#9281f7]/10 bg-[#9281f7]/[0.03] p-3"
          >
            <HelpCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-[#9281f7]/50" />
            <p className="text-sm text-[#a1a4a5] leading-relaxed">{gap}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function ExperimentsSection({ items }: { items: string[] }) {
  if (!items || items.length === 0) return null

  return (
    <div className="rounded-xl border border-[#292d30] bg-[#0a0f14]/50 p-5">
      <SectionHeader
        icon={FlaskConical}
        title="Recommended Experiments"
        count={items.length}
        color="bg-[#70b8ff]/10 text-[#70b8ff]"
      />
      <div className="space-y-2">
        {items.map((exp, i) => (
          <div
            key={i}
            className="flex gap-3 rounded-lg border border-[#70b8ff]/10 bg-[#70b8ff]/[0.03] p-3"
          >
            <FlaskConical className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-[#70b8ff]/50" />
            <p className="text-sm text-[#a1a4a5] leading-relaxed">{exp}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function SourcesSection({ sources }: { sources: string[] }) {
  if (sources.length === 0) return null

  return (
    <div className="rounded-xl border border-[#292d30] bg-black p-5">
      <SectionHeader
        icon={BookOpen}
        title="Sources"
        count={sources.length}
        color="bg-[#3b9eff]/10 text-[#3b9eff]"
      />
      <div className="flex flex-wrap gap-2">
        {sources.map((source, i) => {
          const clean = source.replace(/[\[\]]/g, '').trim()
          return (
            <a
              key={i}
              href={arxivUrl(clean)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#292d30] bg-[#1b1b1b] px-3 py-2 text-sm text-[#70b8ff] transition-all hover:border-[#3b9eff]/40 hover:bg-[#3b9eff]/10"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span className="font-mono">{clean}</span>
              <ExternalLink className="h-3 w-3 text-[#6c6c6c]" />
            </a>
          )
        })}
      </div>
    </div>
  )
}

function ExecutiveSummarySection({ report }: { report?: string }) {
  if (!report) return null

  return (
    <div className="rounded-xl border border-[#292d30] bg-[#0b0e14] p-5">
      <SectionHeader
        icon={Sparkles}
        title="Executive Summary"
        color="bg-[#3b9eff]/10 text-[#3b9eff]"
      />
      <div className="text-sm text-[#d0d0d0] leading-relaxed space-y-3">
        <ReactMarkdown
          components={{
            h1: ({node, ...props}) => <h1 className="text-lg font-bold text-white mt-4 mb-2" {...props} />,
            h2: ({node, ...props}) => <h2 className="text-base font-semibold text-white mt-3 mb-2" {...props} />,
            h3: ({node, ...props}) => <h3 className="text-sm font-semibold text-white mt-2 mb-1" {...props} />,
            p: ({node, ...props}) => <p className="mb-3 last:mb-0" {...props} />,
            ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
            ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
            li: ({node, ...props}) => <li className="text-sm text-[#a1a4a5]" {...props} />,
            strong: ({node, ...props}) => <strong className="font-semibold text-white" {...props} />,
            code: ({node, ...props}) => <code className="bg-white/10 px-1.5 py-0.5 rounded font-mono text-xs text-[#f0f0f0]" {...props} />,
            a: ({node, ...props}) => {
              const text = props.children?.toString() || ''
              if (text.startsWith('arXiv:') || text.match(/^\d{4}\.\d{4,5}$/) || text.startsWith('[arXiv:')) {
                return <CitationChip id={text} />
              }
              return <a className="text-[#70b8ff] hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
            }
          }}
        >
          {report}
        </ReactMarkdown>
      </div>
    </div>
  )
}

interface QueryHistoryItem {
  id: string
  question: string
  timestamp: string
  result: CoordinatorOutput
}

export function QueryPanel() {
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<CoordinatorOutput | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<QueryHistoryItem[]>([])
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)

  // Load history from localStorage on client-side mount
  useEffect(() => {
    setMounted(true)
    const saved = localStorage.getItem('axion_query_history')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed)) {
          setHistory(parsed)
          if (parsed.length > 0) {
            setActiveHistoryId(parsed[0].id)
            setResult(parsed[0].result)
            setQuestion(parsed[0].question)
          }
        }
      } catch (e) {
        console.error('Failed to parse query history:', e)
      }
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || isLoading) return

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const trimmedQ = question.trim()
      const output = await runQuery(trimmedQ)
      setResult(output)

      // Add to history
      const newItem: QueryHistoryItem = {
        id: Math.random().toString(36).substring(7),
        question: trimmedQ,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        result: output,
      }
      const updated = [newItem, ...history]
      setHistory(updated)
      localStorage.setItem('axion_query_history', JSON.stringify(updated))
      setActiveHistoryId(newItem.id)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to get response. Is the API running?'
      )
      setResult(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectHistory = (item: QueryHistoryItem) => {
    setActiveHistoryId(item.id)
    setQuestion(item.question)
    setResult(item.result)
    setError(null)
  }

  const handleDeleteHistory = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const updated = history.filter((item) => item.id !== id)
    setHistory(updated)
    localStorage.setItem('axion_query_history', JSON.stringify(updated))
    if (activeHistoryId === id) {
      if (updated.length > 0) {
        setActiveHistoryId(updated[0].id)
        setQuestion(updated[0].question)
        setResult(updated[0].result)
      } else {
        setActiveHistoryId(null)
        setQuestion('')
        setResult(null)
      }
    }
  }

  const handleNewQuery = () => {
    setActiveHistoryId(null)
    setQuestion('')
    setResult(null)
    setError(null)
  }

  const raw: RawReport = result?.raw ? parseRaw(result.raw) : {}
  const conf = result ? getConfidenceConfig(result.confidence) : null

  if (!mounted) {
    return (
      <div className="rounded-xl border border-[#292d30] p-6 space-y-4">
        <Skeleton className="h-24 w-full bg-[#1b1b1b]" />
        <Skeleton className="h-10 w-24 bg-[#1b1b1b]" />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
      {/* Sidebar - Chat History */}
      <div className="md:col-span-4 border border-[#292d30] rounded-xl bg-black/40 p-4 space-y-4 flex flex-col max-h-[750px] min-h-[400px]">
        <div className="flex items-center justify-between border-b border-[#292d30] pb-3">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-[#3b9eff]" />
            <h3 className="font-semibold text-sm text-[#f0f0f0]">Research History</h3>
          </div>
          <Button
            size="sm"
            onClick={handleNewQuery}
            className="h-8 border border-[#3b9eff]/40 bg-transparent text-[#70b8ff] hover:bg-[#3b9eff]/10 hover:text-white transition-all text-xs flex items-center gap-1"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New Ask</span>
          </Button>
        </div>

        {/* Query List */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {history.length === 0 ? (
            <div className="text-center py-8 text-[#6c6c6c] text-xs">
              No queries run yet. Start a new ask to build history.
            </div>
          ) : (
            history.map((item) => {
              const isActive = item.id === activeHistoryId
              return (
                <div
                  key={item.id}
                  onClick={() => handleSelectHistory(item)}
                  className={`group relative flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                    isActive
                      ? 'border-[#3b9eff] bg-[#3b9eff]/5 text-white'
                      : 'border-[#292d30] bg-[#111] hover:border-[#6c6c6c] hover:bg-[#151515] text-[#a1a4a5]'
                  }`}
                >
                  <MessageSquare className={`h-4 w-4 mt-0.5 flex-shrink-0 ${isActive ? 'text-[#3b9eff]' : 'text-[#6c6c6c]'}`} />
                  <div className="flex-1 pr-6 overflow-hidden">
                    <p className="text-xs font-medium truncate leading-relaxed">{item.question}</p>
                    <span className="text-[10px] text-[#6c6c6c] block mt-1">{item.timestamp}</span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteHistory(item.id, e)}
                    className="absolute right-2 top-2 p-1 rounded hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity text-[#6c6c6c] hover:text-[#ff9592]"
                    title="Delete query history"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="md:col-span-8 space-y-6">
        {/* Question input */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a research question… e.g., What is the current consensus on transformer scaling laws?"
              className="min-h-[120px] w-full resize-none rounded-xl border border-[#292d30] bg-black px-4 py-3 text-[#f0f0f0] placeholder:text-[#6c6c6c] focus:border-[#3b9eff] focus:outline-none focus:ring-1 focus:ring-[#3b9eff]/50 transition-colors"
              disabled={isLoading}
            />
          </div>
          <div className="flex items-center justify-between">
            <p className="text-xs text-[#6c6c6c]">
              The AI will search the knowledge graph and synthesize an answer
            </p>
            <Button
              type="submit"
              disabled={!question.trim() || isLoading}
              className="border border-[#3b9eff] bg-transparent text-white hover:bg-[#3b9eff]/10"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Thinking…</span>
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  <span>Ask</span>
                </>
              )}
            </Button>
          </div>
        </form>

        {/* Loading state */}
        {isLoading && (
          <div className="rounded-xl border border-[#3b9eff]/20 bg-[#3b9eff]/[0.03] p-6 space-y-6">
            <div className="flex items-center gap-3">
              <Loader2 className="h-4 w-4 animate-spin text-[#3b9eff]" />
              <span className="text-[#f0f0f0] font-medium">
                Searching knowledge graph and synthesizing response…
              </span>
            </div>
            <div className="space-y-3">
              <Skeleton className="h-4 w-full bg-[#1b1b1b]" />
              <Skeleton className="h-4 w-5/6 bg-[#1b1b1b]" />
              <Skeleton className="h-4 w-4/5 bg-[#1b1b1b]" />
            </div>
            <div className="border-t border-[#292d30] pt-4 space-y-4">
              <div className="flex gap-2">
                <Skeleton className="h-6 w-24 bg-[#1b1b1b]" />
                <Skeleton className="h-6 w-32 bg-[#1b1b1b]" />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Skeleton className="h-24 w-full bg-[#1b1b1b]" />
                <Skeleton className="h-24 w-full bg-[#1b1b1b]" />
              </div>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="rounded-xl border border-[#ff9592]/30 bg-[#ff9592]/5 p-4">
            <p className="text-sm text-[#ff9592]">{error}</p>
          </div>
        )}

        {/* Result */}
        {result && !isLoading && (
          <div className="space-y-4">
            {/* Header card — Question + confidence */}
            <div className="rounded-xl border border-[#292d30] bg-black p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-[#3b9eff]" />
                    <span className="text-xs font-medium uppercase tracking-wider text-[#6c6c6c]">
                      Research Report
                    </span>
                  </div>
                  <p className="text-[#f0f0f0] font-medium leading-snug">{question}</p>
                </div>
                {conf && (
                  <div
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${conf.bg} ${conf.border}`}
                  >
                    <conf.icon className={`h-4 w-4 ${conf.color}`} />
                    <div className="text-right">
                      <p className={`text-sm font-medium ${conf.color}`}>
                        {Math.round(result.confidence * 100)}%
                      </p>
                      <p className="text-[10px] text-[#6c6c6c]">{conf.label}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Confidence reason */}
              {raw.confidence_reason && (
                <p className="mt-3 text-xs text-[#6c6c6c] border-t border-[#292d30] pt-3">
                  {raw.confidence_reason}
                </p>
              )}

              {/* Meta badges */}
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#292d30] pt-3">
                <Badge
                  variant="outline"
                  className="border-[#292d30] bg-transparent text-[#a1a4a5]"
                >
                  {result.iterations} iteration{result.iterations !== 1 ? 's' : ''}
                </Badge>
                {result.sources.length > 0 && (
                  <Badge
                    variant="outline"
                    className="border-[#292d30] bg-transparent text-[#70b8ff]"
                  >
                    <BookOpen className="mr-1 h-3 w-3" />
                    {result.sources.length} source{result.sources.length !== 1 ? 's' : ''}
                  </Badge>
                )}
                {raw.consensus && (
                  <Badge
                    variant="outline"
                    className="border-[#292d30] bg-transparent text-[#3ad389]"
                  >
                    {raw.consensus.length} consensus point{raw.consensus.length !== 1 ? 's' : ''}
                  </Badge>
                )}
                {raw.disputed && raw.disputed.length > 0 && (
                  <Badge
                    variant="outline"
                    className="border-[#292d30] bg-transparent text-[#ff9592]"
                  >
                    {raw.disputed.length} dispute{raw.disputed.length !== 1 ? 's' : ''}
                  </Badge>
                )}
              </div>
            </div>

            {/* Collapsible reasoning */}
            <div className="rounded-xl border border-[#292d30] bg-black p-4">
              <PlanSteps plan={result.plan} />
              <ReflectionLog steps={result.reflection_log} />
            </div>

            {/* Structured report sections */}
            <ExecutiveSummarySection report={result.report} />
            <ConsensusSection items={raw.consensus} />
            <DisputesSection items={raw.disputed} />
            <GapsSection items={raw.missing} />
            <ExperimentsSection items={raw.recommended_experiments} />
            <SourcesSection sources={result.sources} />
          </div>
        )}
      </div>
    </div>
  )
}
