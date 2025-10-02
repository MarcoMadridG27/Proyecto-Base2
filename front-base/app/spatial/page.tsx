import { Sidebar } from "@/components/sidebar"
import { SpatialResults } from "@/components/spatial-results"

export default function SpatialPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <SpatialResults />
      </main>
    </div>
  )
}
