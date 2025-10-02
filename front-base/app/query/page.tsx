import { Sidebar } from "@/components/sidebar"
import { SQLQuery } from "@/components/sql-query"

export default function QueryPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <SQLQuery />
      </main>
    </div>
  )
}
