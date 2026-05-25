'use client'

import useSWR from 'swr'
import { FileText, MessageSquare, AlertTriangle, Lightbulb } from 'lucide-react'
import { getStats } from '@/lib/api-client'
import { Skeleton } from '@/components/ui/skeleton'
import type { GraphStats } from '@/types/axion'

const statItems = [
  {
    key: 'papers' as const,
    label: 'Papers',
    icon: FileText,
    color: 'text-[#f0f0f0]',
  },
  {
    key: 'claims' as const,
    label: 'Claims',
    icon: MessageSquare,
    color: 'text-[#baa7ff]',
  },
  {
    key: 'contradictions' as const,
    label: 'Contradictions',
    icon: AlertTriangle,
    color: 'text-[#ff9592]',
  },
  {
    key: 'gaps' as const,
    label: 'Research Gaps',
    icon: Lightbulb,
    color: 'text-[#9281f7]',
  },
]

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  isLoading,
}: {
  label: string
  value: number | undefined
  icon: React.ComponentType<{ className?: string }>
  color: string
  isLoading: boolean
}) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-[#292d30] bg-black px-6 py-5">
      <div className={`${color}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-sm text-[#a1a4a5]">{label}</span>
        {isLoading ? (
          <Skeleton className="h-7 w-16 bg-[#1b1b1b]" />
        ) : (
          <span className="text-2xl font-semibold text-[#f0f0f0]">
            {value?.toLocaleString() ?? '—'}
          </span>
        )}
      </div>
    </div>
  )
}

export function DashboardStats() {
  const { data, isLoading, error } = useSWR<GraphStats>('stats', getStats, {
    refreshInterval: 60000, // Refresh every minute
  })

  if (error) {
    return (
      <div className="rounded-xl border border-[#292d30] bg-black px-6 py-4">
        <p className="text-sm text-[#ff9592]">
          Failed to load stats. Is the API server running?
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {statItems.map((item) => (
        <StatCard
          key={item.key}
          label={item.label}
          value={data?.[item.key]}
          icon={item.icon}
          color={item.color}
          isLoading={isLoading}
        />
      ))}
    </div>
  )
}
