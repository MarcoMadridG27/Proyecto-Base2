import { Sidebar } from "@/components/sidebar"
import { TextSearch } from "@/components/text-search"

export default function TextSearchPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <TextSearch />
      </main>
    </div>
  )
}
