import { Sidebar } from "@/components/sidebar"
import MultimediaSearch from "@/components/multimedia-search"

export default function MultimediaSearchPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <MultimediaSearch />
      </main>
    </div>
  )
}
