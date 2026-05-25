'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { RefreshCw, Clock, FileText, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getIngestionStatus, triggerIngestion } from '@/lib/api-client'
import type { IngestionStatus as IngestionStatusType } from '@/types/axion'

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

export function IngestionStatus() {
  const [isTriggering, setIsTriggering] = useState(false)
  
  const { data, isLoading, mutate } = useSWR<IngestionStatusType>(
    'ingestion-status',
    getIngestionStatus,
    {
      refreshInterval: 30000, // Refresh every 30 seconds
    }
  )

  const handleTrigger = async () => {
    setIsTriggering(true)
    try {
      await triggerIngestion()
      // Start polling more frequently
      const pollInterval = setInterval(async () => {
        const status = await getIngestionStatus()
        mutate(status, false)
        if (!status.running) {
          clearInterval(pollInterval)
        }
      }, 5000)
    } catch (error) {
      console.error('Failed to trigger ingestion:', error)
    } finally {
      setIsTriggering(false)
    }
  }

  const isRunning = data?.running || isTriggering

  return (
    <div className="flex items-center gap-4">
      {/* Status indicators */}
      <div className="hidden items-center gap-4 text-sm sm:flex">
        {!isLoading && data && (
          <>
            <div className="flex items-center gap-2 text-[#a1a4a5]">
              <Clock className="h-4 w-4" />
              <span>{formatRelativeTime(data.last_run)}</span>
            </div>
            {data.new_papers > 0 && (
              <div className="flex items-center gap-1.5 text-[#3ad389]">
                <FileText className="h-4 w-4" />
                <span>+{data.new_papers}</span>
              </div>
            )}
            {data.new_claims > 0 && (
              <div className="flex items-center gap-1.5 text-[#baa7ff]">
                <MessageSquare className="h-4 w-4" />
                <span>+{data.new_claims}</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Trigger button */}
      <Button
        variant="outline"
        size="sm"
        onClick={handleTrigger}
        disabled={isRunning}
        className="border-[#292d30] bg-transparent text-[#f0f0f0] hover:border-[#3b9eff] hover:bg-transparent"
      >
        <RefreshCw
          className={`h-4 w-4 ${isRunning ? 'animate-spin text-[#3b9eff]' : ''}`}
        />
        <span className="hidden sm:inline">
          {isRunning ? 'Ingesting...' : 'Ingest'}
        </span>
      </Button>
    </div>
  )
}
