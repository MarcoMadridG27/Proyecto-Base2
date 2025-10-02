import { Sidebar } from "@/components/sidebar"
import { Dashboard } from "@/components/dashboard"

export default function Home() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Dashboard />
      </main>
    </div>
  )
}
