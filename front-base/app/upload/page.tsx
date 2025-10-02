import { Sidebar } from "@/components/sidebar"
import { FileUpload } from "@/components/file-upload"

export default function UploadPage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <FileUpload />
      </main>
    </div>
  )
}
