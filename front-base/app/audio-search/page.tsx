import MultimediaSearch from "@/components/multimedia-audio"
import { Sidebar } from "@/components/sidebar"

export default function Page() {
  return (<div className="flex h-screen bg-background">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <MultimediaSearch focus="audio" initialTab="search" />
        </main>
      </div>)
}
