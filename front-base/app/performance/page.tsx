import { Sidebar } from "@/components/sidebar"
import { PerformanceBenchmark } from "@/components/performance-benchmark"

export default function PerformancePage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <PerformanceBenchmark />
      </main>
    </div>
  )
}
