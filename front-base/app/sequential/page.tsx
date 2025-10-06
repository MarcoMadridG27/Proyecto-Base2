import { Sidebar } from "@/components/sidebar"
import { SequentialViz } from "@/components/sequential-viz"

export default function SequentialPage() {
	return (
		<div className="flex h-screen bg-background">
			<Sidebar />
			<main className="flex-1 overflow-auto">
				<SequentialViz />
			</main>
		</div>
	)
}


