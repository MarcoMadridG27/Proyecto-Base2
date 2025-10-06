"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "sonner"

type SeqInfo = {
	table: string
	column: string
	aux_limit: number
	main_count: number
	aux_count: number
	sample_main: [string, number][]
	sample_aux: [string, number][]
}

export function SequentialViz() {
	const [tableName, setTableName] = useState("")
	const [columnName, setColumnName] = useState("")
	const [info, setInfo] = useState<SeqInfo | null>(null)

	useEffect(() => {
		try {
			const t = localStorage.getItem("seq_viz_table")
			const c = localStorage.getItem("seq_viz_col")
			if (t) setTableName(t)
			if (c) setColumnName(c)
		} catch {}
	}, [])

	useEffect(() => { try { localStorage.setItem("seq_viz_table", tableName) } catch {} }, [tableName])
	useEffect(() => { try { localStorage.setItem("seq_viz_col", columnName) } catch {} }, [columnName])

	const loadInfo = async () => {
		if (!tableName || !columnName) {
			toast.error("Missing inputs", { description: "Provide table and column" })
			return
		}
		try {
			const res = await fetch(`http://localhost:8000/sequential_index_info?table_name=${encodeURIComponent(tableName)}&column=${encodeURIComponent(columnName)}`)
			const data = await res.json()
			if (!data.ok) throw new Error(data.error || "Failed to load")
			setInfo(data.info)
		} catch (e:any) {
			toast.error("Load failed", { description: e.message })
		}
	}

	return (
		<div className="p-8 space-y-8">
			<div className="animate-fade-in">
				<h1 className="text-3xl font-bold">Sequential Index Visualizer</h1>
				<p className="text-muted-foreground">View main and auxiliary areas for a sequential index</p>
			</div>
			<Card className="glass-card">
				<CardHeader>
					<CardTitle>Target</CardTitle>
					<CardDescription>Enter table and column with an existing sequential index</CardDescription>
				</CardHeader>
				<CardContent className="flex gap-3">
					<Input placeholder="table name" value={tableName} onChange={e => setTableName(e.target.value)} className="max-w-xs" />
					<Input placeholder="column name" value={columnName} onChange={e => setColumnName(e.target.value)} className="max-w-xs" />
					<Button onClick={loadInfo}>Load</Button>
				</CardContent>
			</Card>

			{info && (
				<div className="grid md:grid-cols-2 gap-6">
					<Card>
						<CardHeader>
							<CardTitle>Main Area</CardTitle>
							<CardDescription>
								{info.main_count} entries (sorted) — aux limit: {info.aux_limit}
							</CardDescription>
						</CardHeader>
						<CardContent>
							<Table>
								<TableHeader>
									<TableRow>
										<TableHead>Key</TableHead>
										<TableHead>Offset</TableHead>
									</TableRow>
								</TableHeader>
								<TableBody>
									{info.sample_main.map((row, i) => (
										<TableRow key={i}>
											<TableCell>{row[0]}</TableCell>
											<TableCell>{row[1]}</TableCell>
										</TableRow>
									))}
								</TableBody>
							</Table>
						</CardContent>
					</Card>
					<Card>
						<CardHeader>
							<CardTitle>Auxiliary Area</CardTitle>
							<CardDescription>{info.aux_count} pending entries</CardDescription>
						</CardHeader>
						<CardContent>
							<Table>
								<TableHeader>
									<TableRow>
										<TableHead>Key</TableHead>
										<TableHead>Offset</TableHead>
									</TableRow>
								</TableHeader>
								<TableBody>
									{info.sample_aux.map((row, i) => (
										<TableRow key={i}>
											<TableCell>{row[0]}</TableCell>
											<TableCell>{row[1]}</TableCell>
										</TableRow>
									))}
								</TableBody>
							</Table>
						</CardContent>
					</Card>
				</div>
			)}
		</div>
	)
}


