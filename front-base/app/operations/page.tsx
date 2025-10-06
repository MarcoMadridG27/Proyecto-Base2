import { Sidebar } from "@/components/sidebar"
import { IndexOperations } from "@/components/index-operations"

export default function OperationsPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <IndexOperations />
      </main>
    </div>
  )
}
