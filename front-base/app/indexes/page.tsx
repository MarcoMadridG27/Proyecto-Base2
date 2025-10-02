import { Sidebar } from "@/components/sidebar"
import { IndexExplorer } from "@/components/index-explorer"

export default function IndexesPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <IndexExplorer />
      </main>
    </div>
  )
}
