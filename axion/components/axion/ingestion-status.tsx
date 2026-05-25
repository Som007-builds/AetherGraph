'use client'

import { useState, useEffect, useRef } from 'react'
import useSWR from 'swr'
import {
  RefreshCw,
  Clock,
  FileText,
  MessageSquare,
  Play,
  CheckCircle,
  AlertCircle,
  Terminal,
  ArrowRight,
  Database,
  Search,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  getIngestionStatus,
  triggerIngestion,
  runCustomIngestion,
  getIngestionProgress,
} from '@/lib/api-client'
import type { IngestionStatus as IngestionStatusType, CustomIngestionProgress } from '@/types/axion'

function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never'
  
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function formatDuration(seconds: number): string {
  if (seconds <= 0) return 'Calculating...'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

export function IngestionStatus() {
  const [isOpen, setIsOpen] = useState(false)
  const [topic, setTopic] = useState('')
  const [limit, setLimit] = useState(5)
  const [customProgress, setCustomProgress] = useState<CustomIngestionProgress | null>(null)
  const [isTriggering, setIsTriggering] = useState(false)
  const [pollingActive, setPollingActive] = useState(false)
  const [triggerError, setTriggerError] = useState<string | null>(null)

  const consoleEndRef = useRef<HTMLDivElement | null>(null)

  // Fetch general background cron ingestion status
  const { data: generalStatus, mutate: mutateGeneral } = useSWR<IngestionStatusType>(
    'ingestion-status',
    getIngestionStatus,
    {
      refreshInterval: 30000,
    }
  )

  // Sync / poll custom progress when sheet is open or polling is active
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null

    const fetchProgress = async () => {
      try {
        const progress = await getIngestionProgress()
        setCustomProgress(progress)
        
        if (progress.running) {
          setPollingActive(true)
        } else {
          setPollingActive(false)
        }
      } catch (err) {
        console.error('Error fetching custom ingestion progress:', err)
      }
    }

    // Run once immediately on sheet open or poll toggle
    if (isOpen || pollingActive) {
      fetchProgress()
    }

    // Set up polling interval if active
    if (pollingActive || (isOpen && customProgress?.running)) {
      intervalId = setInterval(fetchProgress, 2000)
    }

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [isOpen, pollingActive, customProgress?.running])

  // Auto-scroll terminal log to bottom on updates
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [customProgress?.logs])

  const handleStartCustomIngest = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!topic.trim() || isTriggering) return

    setIsTriggering(true)
    setTriggerError(null)

    try {
      await runCustomIngestion(topic.trim(), limit)
      setPollingActive(true)
      // Mutate general status to reflect running state
      mutateGeneral()
    } catch (err) {
      setTriggerError(err instanceof Error ? err.message : 'Failed to start ingestion pipeline')
    } finally {
      setIsTriggering(false)
    }
  }

  const handleResetProgressView = async () => {
    try {
      // Refresh the final stats
      mutateGeneral()
      setTopic('')
      setLimit(5)
      setCustomProgress(null)
      setPollingActive(false)
      setTriggerError(null)
    } catch (e) {
      console.error(e)
    }
  }

  const handleTriggerDefaultIngest = async () => {
    setIsTriggering(true)
    try {
      await triggerIngestion()
      mutateGeneral()
    } catch (err) {
      console.error('Failed to trigger default cron:', err)
    } finally {
      setIsTriggering(false)
    }
  }

  const isAnyIngestionRunning = generalStatus?.running || customProgress?.running || isTriggering

  return (
    <div className="flex items-center gap-4">
      {/* Stats bar */}
      <div className="hidden items-center gap-4 text-sm sm:flex">
        {generalStatus && (
          <>
            <div className="flex items-center gap-2 text-[#a1a4a5]">
              <Clock className="h-4 w-4" />
              <span>{formatRelativeTime(generalStatus.last_run)}</span>
            </div>
            {generalStatus.new_papers > 0 && (
              <div className="flex items-center gap-1.5 text-[#3ad389]">
                <FileText className="h-4 w-4" />
                <span>+{generalStatus.new_papers}</span>
              </div>
            )}
            {generalStatus.new_claims > 0 && (
              <div className="flex items-center gap-1.5 text-[#baa7ff]">
                <MessageSquare className="h-4 w-4" />
                <span>+{generalStatus.new_claims}</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Main Sheet Trigger */}
      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="border-[#292d30] bg-transparent text-[#f0f0f0] hover:border-[#3b9eff] hover:bg-transparent flex items-center gap-2"
          >
            <RefreshCw
              className={`h-4 w-4 ${isAnyIngestionRunning ? 'animate-spin text-[#3b9eff]' : ''}`}
            />
            <span>{isAnyIngestionRunning ? 'Ingesting...' : 'Ingest'}</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="right" className="border-l border-[#292d30] bg-black text-[#f0f0f0] w-full sm:max-w-md flex flex-col h-full overflow-hidden">
          <SheetHeader className="pb-4 border-b border-[#292d30]">
            <SheetTitle className="text-white text-lg flex items-center gap-2">
              <Database className="h-5 w-5 text-[#3b9eff]" />
              <span>Ingestion Pipeline</span>
            </SheetTitle>
            <SheetDescription className="text-[#6c6c6c] text-xs">
              Feed new ArXiv publications into the multi-agent claims graph.
            </SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto py-6 space-y-6">
            {/* Conditional Content */}
            {!customProgress || (customProgress.status === 'idle' && !customProgress.running) ? (
              /* Pipeline Form State */
              <form onSubmit={handleStartCustomIngest} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="topic-input" className="text-[#a1a4a5] text-xs">
                    Research Field / Topic
                  </Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#6c6c6c]" />
                    <Input
                      id="topic-input"
                      type="text"
                      required
                      placeholder="e.g., direct preference optimization"
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      className="pl-9 border-[#292d30] bg-black/60 focus-visible:border-[#3b9eff] focus-visible:ring-1 focus-visible:ring-[#3b9eff]/50"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="limit-input" className="text-[#a1a4a5] text-xs flex justify-between">
                    <span>Target Papers Limit</span>
                    <span className="text-[#6c6c6c] font-mono">{limit}</span>
                  </Label>
                  <Input
                    id="limit-input"
                    type="number"
                    min={1}
                    max={20}
                    value={limit}
                    onChange={(e) => setLimit(parseInt(e.target.value) || 5)}
                    className="border-[#292d30] bg-black/60 focus-visible:border-[#3b9eff] focus-visible:ring-1 focus-visible:ring-[#3b9eff]/50"
                  />
                </div>

                {triggerError && (
                  <div className="flex items-center gap-2 text-xs text-[#ff9592] bg-[#ff9592]/5 border border-[#ff9592]/20 p-3 rounded-lg">
                    <AlertCircle className="h-4 w-4 flex-shrink-0" />
                    <span>{triggerError}</span>
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={isTriggering}
                  className="w-full border border-[#3ad389]/40 bg-transparent text-[#3ad389] hover:bg-[#3ad389]/10 transition-all flex items-center justify-center gap-2 h-10 font-medium"
                >
                  <Play className="h-4 w-4" />
                  <span>{isTriggering ? 'Starting Pipeline...' : 'Start Pipeline'}</span>
                </Button>

                <div className="pt-4 border-t border-[#292d30] space-y-3">
                  <p className="text-[11px] text-[#6c6c6c] leading-relaxed">
                    Alternatively, trigger a quick background incremental search on pre-configured fields:
                  </p>
                  <Button
                    type="button"
                    onClick={handleTriggerDefaultIngest}
                    disabled={isAnyIngestionRunning}
                    className="w-full border border-[#292d30] bg-transparent text-[#a1a4a5] hover:text-[#f0f0f0] hover:bg-white/5 transition-all text-xs flex items-center justify-center gap-1.5 h-9"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span>Trigger Cron Job Ingest</span>
                  </Button>
                </div>
              </form>
            ) : (
              /* Pipeline Active or Completed/Failed State */
              <div className="space-y-6">
                {/* Status Box */}
                <div className="rounded-xl border border-[#292d30] bg-black/40 p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <span className="text-[10px] text-[#6c6c6c] uppercase tracking-wider block">
                        Topic: "{customProgress.topic}"
                      </span>
                      <h4 className="font-semibold text-sm capitalize text-white">
                        {customProgress.status === 'processing'
                          ? `Ingesting Paper ${customProgress.current_index}/${customProgress.limit}`
                          : customProgress.status === 'contradiction'
                          ? 'Checking Contradictions'
                          : customProgress.status === 'confidence'
                          ? 'Propagating Belief updates'
                          : customProgress.status}
                      </h4>
                    </div>

                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-mono ${
                        customProgress.status === 'completed'
                          ? 'bg-[#3ad389]/10 text-[#3ad389]'
                          : customProgress.status === 'failed'
                          ? 'bg-[#ff9592]/10 text-[#ff9592]'
                          : 'bg-[#3b9eff]/10 text-[#3b9eff]'
                      }`}
                    >
                      {customProgress.percent}%
                    </span>
                  </div>

                  <Progress value={customProgress.percent} className="h-1.5 bg-[#1b1b1b]" />

                  {/* Dynamic Estimates */}
                  {customProgress.running && (
                    <div className="flex items-center justify-between border-t border-[#292d30] pt-3 text-xs">
                      <span className="text-[#6c6c6c]">Estimated Time Remaining:</span>
                      <span className="font-mono text-[#f0f0f0] font-semibold flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5 text-[#3b9eff]" />
                        {formatDuration(customProgress.remaining_seconds)}
                      </span>
                    </div>
                  )}
                </div>

                {/* Pipeline Stats Summary */}
                <div className="grid grid-cols-3 gap-3 border border-[#292d30] rounded-xl p-3 bg-black/20 text-center">
                  <div className="space-y-1">
                    <span className="text-[10px] text-[#6c6c6c] block">Papers Added</span>
                    <span className="font-semibold text-sm text-[#f0f0f0]">
                      {customProgress.papers_added}
                    </span>
                  </div>
                  <div className="space-y-1 border-x border-[#292d30]">
                    <span className="text-[10px] text-[#6c6c6c] block">Claims Found</span>
                    <span className="font-semibold text-sm text-[#f0f0f0]">
                      {customProgress.claims_added}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-[#6c6c6c] block">Contradictions</span>
                    <span className="font-semibold text-sm text-[#f0f0f0]">
                      {customProgress.contradictions_found}
                    </span>
                  </div>
                </div>

                {/* Active Paper Card */}
                {customProgress.current_paper_id && (
                  <div className="rounded-xl border border-[#3b9eff]/20 bg-[#3b9eff]/[0.02] p-4 space-y-2">
                    <span className="text-[10px] font-medium text-[#3b9eff] uppercase tracking-wider block">
                      Active: {customProgress.current_paper_id}
                    </span>
                    <p className="text-xs font-semibold text-[#f0f0f0] leading-snug line-clamp-2">
                      {customProgress.current_paper_title}
                    </p>
                    <div className="flex items-center gap-2 text-[11px] text-[#6c6c6c] pt-1">
                      <span className="animate-pulse inline-block h-1.5 w-1.5 rounded-full bg-[#3b9eff]" />
                      <span>{customProgress.current_step}</span>
                    </div>
                  </div>
                )}

                {/* Live Console Logs */}
                <div className="space-y-2">
                  <Label className="text-[#a1a4a5] text-xs flex items-center gap-1.5">
                    <Terminal className="h-4 w-4 text-[#baa7ff]" />
                    <span>Real-time Ingestion Console</span>
                  </Label>
                  <div className="bg-[#080808] border border-[#292d30] rounded-xl p-3 font-mono text-[10px] text-[#8e9193] h-60 overflow-y-auto space-y-1.5 scrollbar-thin">
                    {customProgress.logs.map((log, idx) => (
                      <div key={idx} className="whitespace-pre-wrap leading-normal font-mono break-all">
                        {log}
                      </div>
                    ))}
                    <div ref={consoleEndRef} />
                    {customProgress.running && (
                      <div className="animate-pulse inline-block w-1.5 h-3 bg-[#3b9eff] align-middle" />
                    )}
                  </div>
                </div>

                {/* Terminal Success/Failure block */}
                {!customProgress.running && (
                  <div className="space-y-4">
                    {customProgress.status === 'completed' && (
                      <div className="rounded-xl border border-[#3ad389]/20 bg-[#3ad389]/5 p-4 flex items-start gap-3">
                        <CheckCircle className="h-5 w-5 text-[#3ad389] flex-shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          <h5 className="font-semibold text-xs text-[#3ad389]">Ingestion Success</h5>
                          <p className="text-[11px] text-[#a1a4a5] leading-relaxed">
                            Knowledge graph migration, claim vectorization, and conflict checks are complete.
                          </p>
                        </div>
                      </div>
                    )}
                    {customProgress.status === 'failed' && (
                      <div className="rounded-xl border border-[#ff9592]/20 bg-[#ff9592]/5 p-4 flex items-start gap-3">
                        <AlertCircle className="h-5 w-5 text-[#ff9592] flex-shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          <h5 className="font-semibold text-xs text-[#ff9592]">Ingestion Interrupted</h5>
                          <p className="text-[11px] text-[#a1a4a5] leading-relaxed">
                            {customProgress.error_message || 'An error occurred during claims synthesis.'}
                          </p>
                        </div>
                      </div>
                    )}

                    <Button
                      onClick={handleResetProgressView}
                      className="w-full border border-[#292d30] bg-transparent text-[#a1a4a5] hover:text-[#f0f0f0] hover:bg-white/5 transition-all text-xs flex items-center justify-center gap-1.5 h-10"
                    >
                      <span>Trigger New Ingestion</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
