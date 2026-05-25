import { DashboardStats } from '@/components/axion/dashboard-stats'
import { IngestionStatus } from '@/components/axion/ingestion-status'
import { QueryPanel } from '@/components/axion/query-panel'
import { ContradictionList } from '@/components/axion/contradiction-list'
import { GapList } from '@/components/axion/gap-list'
import { TimelineView } from '@/components/axion/timeline-view'
import { GraphEvolution } from '@/components/axion/graph-evolution'
import { KnowledgeGraph } from '@/components/axion/knowledge-graph'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MessageSquare, AlertTriangle, Lightbulb, Calendar, TrendingUp, Network } from 'lucide-react'

export default function AxionDashboard() {
  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <header className="border-b border-[#292d30] bg-black">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#3b9eff]/10 border border-[#3b9eff]/30">
              <span className="font-mono text-sm font-bold text-[#3b9eff]">A</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-[#f0f0f0]">Axion</h1>
              <p className="text-xs text-[#6c6c6c]">AI Research Knowledge Graph</p>
            </div>
          </div>
          <IngestionStatus />
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-[1200px] px-6 py-8">
        {/* Stats bar */}
        <section className="mb-8">
          <DashboardStats />
        </section>

        {/* Tab navigation */}
        <Tabs defaultValue="query" className="space-y-6">
          <TabsList className="h-auto w-full justify-start gap-1 rounded-xl border border-[#292d30] bg-black p-2">
            <TabsTrigger
              value="query"
              className="rounded-lg border-0 bg-transparent px-4 py-2 text-[#a1a4a5] data-[state=active]:bg-[#1b1b1b] data-[state=active]:text-[#f0f0f0] data-[state=active]:shadow-none"
            >
              <MessageSquare className="h-4 w-4" />
              <span>Ask a Question</span>
            </TabsTrigger>
            <TabsTrigger
              value="contradictions"
              className="rounded-lg border-0 bg-transparent px-4 py-2 text-[#a1a4a5] data-[state=active]:bg-[#1b1b1b] data-[state=active]:text-[#f0f0f0] data-[state=active]:shadow-none"
            >
              <AlertTriangle className="h-4 w-4" />
              <span>Contradictions</span>
            </TabsTrigger>
            <TabsTrigger
              value="gaps"
              className="rounded-lg border-0 bg-transparent px-4 py-2 text-[#a1a4a5] data-[state=active]:bg-[#1b1b1b] data-[state=active]:text-[#f0f0f0] data-[state=active]:shadow-none"
            >
              <Lightbulb className="h-4 w-4" />
              <span>Research Gaps</span>
            </TabsTrigger>
            <TabsTrigger
              value="timeline"
              className="rounded-lg border-0 bg-transparent px-4 py-2 text-[#a1a4a5] data-[state=active]:bg-[#1b1b1b] data-[state=active]:text-[#f0f0f0] data-[state=active]:shadow-none"
            >
              <Calendar className="h-4 w-4" />
              <span>Timeline</span>
            </TabsTrigger>
            <TabsTrigger
              value="evolution"
              className="rounded-lg border-0 bg-transparent px-4 py-2 text-[#a1a4a5] data-[state=active]:bg-[#1b1b1b] data-[state=active]:text-[#f0f0f0] data-[state=active]:shadow-none"
            >
              <TrendingUp className="h-4 w-4" />
              <span>Graph Evolution</span>
            </TabsTrigger>
            <TabsTrigger
              value="knowledge-graph"
              className="rounded-lg border-0 bg-transparent px-4 py-2 text-[#a1a4a5] data-[state=active]:bg-[#1b1b1b] data-[state=active]:text-[#f0f0f0] data-[state=active]:shadow-none"
            >
              <Network className="h-4 w-4" />
              <span>Knowledge Graph</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="query" className="mt-0">
            <QueryPanel />
          </TabsContent>

          <TabsContent value="contradictions" className="mt-0">
            <ContradictionList />
          </TabsContent>

          <TabsContent value="gaps" className="mt-0">
            <GapList />
          </TabsContent>

          <TabsContent value="timeline" className="mt-0">
            <TimelineView />
          </TabsContent>

          <TabsContent value="evolution" className="mt-0">
            <GraphEvolution />
          </TabsContent>

          <TabsContent value="knowledge-graph" className="mt-0">
            <KnowledgeGraph />
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#292d30] bg-black py-6">
        <div className="mx-auto max-w-[1200px] px-6">
          <p className="text-center text-xs text-[#6c6c6c]">
            Axion v7.0 — AI-powered research knowledge graph
          </p>
        </div>
      </footer>
    </div>
  )
}
