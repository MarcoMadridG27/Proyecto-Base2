import { Sidebar } from "@/components/sidebar"
import { HelpDocumentation } from "@/components/help-documentation"

export default function HelpPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <HelpDocumentation />
      </main>
    </div>
  )
}
