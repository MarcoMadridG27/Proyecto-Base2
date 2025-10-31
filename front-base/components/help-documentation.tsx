"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { HelpCircle, BookOpen, Code2, Github, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"

export function HelpDocumentation() {
  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-foreground/70 bg-clip-text text-transparent">
          Help & Documentation
        </h1>
        <p className="text-muted-foreground mt-2">
          Guía de uso, ejemplos y referencias del sistema UTEC Multimodal DB
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="guide" className="space-y-6">
        <TabsList className="grid w-full max-w-2xl grid-cols-4 bg-white/5 border border-white/10">
          <TabsTrigger value="guide">Quick Guide</TabsTrigger>
          <TabsTrigger value="examples">Examples</TabsTrigger>
          <TabsTrigger value="queries">Queries</TabsTrigger>
          <TabsTrigger value="resources">Resources</TabsTrigger>
        </TabsList>

        {/* Quick Guide Tab */}
        <TabsContent value="guide" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                Quick Start Guide
              </CardTitle>
              <CardDescription>Get started with the UTEC Multimodal Database System</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Step 1 */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    1
                  </div>
                  <h3 className="text-lg font-semibold">Upload Data</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Go to <span className="font-mono text-primary">File Upload</span> and upload your CSV file.
                  The system will automatically detect column types and create a table.
                </p>
              </div>

              {/* Step 2 */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    2
                  </div>
                  <h3 className="text-lg font-semibold">Create Indexes</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Use <span className="font-mono text-primary">Index Explorer</span> to create indexes on
                  your tables. Choose between Sequential, B-Tree, ISAM, Hash, or R-Tree indexes.
                </p>
              </div>

              {/* Step 3 */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    3
                  </div>
                  <h3 className="text-lg font-semibold">Query Data</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Write SQL queries in <span className="font-mono text-primary">SQL Query</span> to search
                  your data. Use indexes for faster retrieval. Compare performance with and without indexes.
                </p>
              </div>

              {/* Step 4 */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    4
                  </div>
                  <h3 className="text-lg font-semibold">Analyze Results</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Use <span className="font-mono text-primary">Performance & Benchmark</span> to visualize
                  query performance metrics and compare different search techniques.
                </p>
              </div>

              {/* Step 5 */}
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    5
                  </div>
                  <h3 className="text-lg font-semibold">Advanced Search</h3>
                </div>
                <p className="text-sm text-muted-foreground ml-11">
                  Try <span className="font-mono text-primary">Text Search</span> for TF-IDF and
                  Cosine Similarity searches, or <span className="font-mono text-primary">Multimedia Search</span> for
                  image and audio similarity queries.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Features Overview */}
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>Available Features</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {[
                  {
                    title: "SQL Query Support",
                    desc: "Full SQL support with SELECT, INSERT, DELETE, WHERE, BETWEEN, and JOIN operations",
                  },
                  {
                    title: "Multiple Index Types",
                    desc: "Sequential, B-Tree, ISAM, Extendible Hash, and R-Tree spatial indexes",
                  },
                  {
                    title: "Text Retrieval",
                    desc: "TF-IDF and Cosine Similarity based text search with ranked results",
                  },
                  {
                    title: "Multimedia Search",
                    desc: "Content-based image and audio similarity search using embeddings",
                  },
                  {
                    title: "Performance Metrics",
                    desc: "Real-time execution time tracking and benchmark comparisons",
                  },
                  {
                    title: "CSV Import",
                    desc: "Automatic column type detection and data validation on upload",
                  },
                ].map((feature, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
                  >
                    <h4 className="font-semibold text-foreground mb-1">{feature.title}</h4>
                    <p className="text-xs text-muted-foreground">{feature.desc}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Examples Tab */}
        <TabsContent value="examples" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code2 className="h-5 w-5 text-primary" />
                Usage Examples
              </CardTitle>
              <CardDescription>Common use cases and workflows</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Example 1 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Example 1: Upload and Search</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm">
                  <p className="text-blue-400">
                    1. Upload a file (cities_1k.csv) via File Upload
                  </p>
                  <p className="text-blue-400">2. System creates table: cities_1k</p>
                  <p className="text-blue-400">
                    3. Query: SELECT * FROM cities_1k WHERE id = 5
                  </p>
                  <p className="text-green-400">Result: Fast with index on id</p>
                </div>
              </div>

              {/* Example 2 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Example 2: Text Search</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm">
                  <p className="text-blue-400">
                    1. Go to Text Search
                  </p>
                  <p className="text-blue-400">
                    2. Enter query: "database optimization"
                  </p>
                  <p className="text-blue-400">3. Select Top-K: 10 results</p>
                  <p className="text-blue-400">4. Choose method: TF-IDF & Cosine</p>
                  <p className="text-green-400">Result: Ranked documents by relevance</p>
                </div>
              </div>

              {/* Example 3 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Example 3: Multimedia Search</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm">
                  <p className="text-blue-400">
                    1. Go to Multimedia Search
                  </p>
                  <p className="text-blue-400">
                    2. Upload an image (landscape.jpg)
                  </p>
                  <p className="text-blue-400">3. Click "Find Similar"</p>
                  <p className="text-green-400">
                    Result: Grid of similar images with similarity scores
                  </p>
                </div>
              </div>

              {/* Example 4 */}
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Example 4: Performance Comparison</h4>
                <div className="rounded-lg bg-black/30 border border-white/10 p-4 font-mono text-sm">
                  <p className="text-blue-400">
                    1. Go to Performance & Benchmark
                  </p>
                  <p className="text-blue-400">2. Select "Text Retrieval" tab</p>
                  <p className="text-blue-400">
                    3. View SPIMI vs PostgreSQL comparison
                  </p>
                  <p className="text-green-400">
                    Result: Graphs showing time and precision tradeoffs
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Queries Tab */}
        <TabsContent value="queries" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle>SQL Query Reference</CardTitle>
              <CardDescription>Common SQL patterns and syntax</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  title: "Simple SELECT",
                  query: "SELECT * FROM table_name;",
                  desc: "Retrieve all records from a table",
                },
                {
                  title: "SELECT with WHERE",
                  query: "SELECT * FROM cities WHERE population > 50000;",
                  desc: "Filter records by condition",
                },
                {
                  title: "SELECT with BETWEEN",
                  query: "SELECT * FROM cities WHERE id BETWEEN 100 AND 500;",
                  desc: "Range queries (uses indexes efficiently)",
                },
                {
                  title: "SELECT with ORDER BY",
                  query: "SELECT * FROM cities ORDER BY population DESC LIMIT 10;",
                  desc: "Sort results and limit output",
                },
                {
                  title: "INSERT Record",
                  query:
                    "INSERT INTO cities (id, name, population) VALUES (999, 'New City', 100000);",
                  desc: "Add a new record",
                },
                {
                  title: "DELETE Records",
                  query: "DELETE FROM cities WHERE id > 1000;",
                  desc: "Remove records matching condition",
                },
                {
                  title: "CREATE INDEX",
                  query: "CREATE INDEX btree ON cities (population);",
                  desc: "Create a B-Tree index for faster queries",
                },
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <h4 className="font-semibold text-foreground mb-2">{item.title}</h4>
                  <div className="bg-black/30 rounded p-2 mb-2 font-mono text-sm text-green-400 overflow-x-auto">
                    {item.query}
                  </div>
                  <p className="text-xs text-muted-foreground">{item.desc}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Resources Tab */}
        <TabsContent value="resources" className="space-y-6 animate-fade-in">
          <Card className="glass-card border-white/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ExternalLink className="h-5 w-5 text-primary" />
                Resources & Links
              </CardTitle>
              <CardDescription>External documentation and project links</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                {
                  icon: Github,
                  title: "GitHub Repository",
                  desc: "Access the source code and project documentation",
                  link: "https://github.com/MarcoMadridG27/Proyecto-Base2",
                },
                {
                  icon: BookOpen,
                  title: "Project Report",
                  desc: "Full project specification and requirements (Proyecto 2)",
                  link: "#",
                },
                {
                  icon: Code2,
                  title: "API Documentation",
                  desc: "Backend API endpoints and request/response formats",
                  link: "http://localhost:8000/docs",
                },
              ].map((resource, idx) => {
                const Icon = resource.icon
                return (
                  <a
                    key={idx}
                    href={resource.link}
                    target={resource.link.startsWith("http") ? "_blank" : "_self"}
                    rel={resource.link.startsWith("http") ? "noopener noreferrer" : undefined}
                    className={cn(
                      "block p-4 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 hover:border-primary/50 transition-all duration-300 group cursor-pointer"
                    )}
                  >
                    <div className="flex items-start gap-4">
                      <Icon className="h-5 w-5 text-primary mt-1 group-hover:scale-110 transition-transform" />
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {resource.title}
                        </h4>
                        <p className="text-sm text-muted-foreground mt-1">{resource.desc}</p>
                      </div>
                      <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0 mt-1" />
                    </div>
                  </a>
                )
              })}
            </CardContent>
          </Card>

          {/* Contact & Support */}
          <Card className="glass-card border-white/10 bg-gradient-to-br from-primary/10 to-secondary/10">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-primary" />
                Need Help?
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-foreground mb-4">
                For issues, feature requests, or questions about the system, please:
              </p>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  • Check this Help section for common questions and examples
                </p>
                <p>
                  • Visit the GitHub repository and create an issue
                </p>
                <p>
                  • Review the project documentation and API docs
                </p>
                <p>
                  • Contact the development team for urgent support
                </p>
              </div>
              <Button className="mt-6 w-full bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80 text-primary-foreground shadow-lg shadow-primary/30">
                <Github className="h-4 w-4 mr-2" />
                Visit GitHub Repository
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
