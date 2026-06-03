import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { apiClient, QueryResponse, SourceChunk } from '../lib/api'

export default function QueryPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!query.trim()) {
      setError('Please enter a query')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await apiClient.query(query, 5)
      setResult(response)
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : 'Failed to query documents'
      setError(`Error: ${errorMsg}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      {/* Navigation */}
      <nav className="bg-slate-950 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-white">RAG Pipeline</h1>
          <div className="flex gap-6">
            <Link
              href="/"
              className="text-blue-400 hover:text-blue-300 transition-colors font-semibold"
            >
              Query
            </Link>
            <Link
              href="/ingest"
              className="text-slate-300 hover:text-white transition-colors"
            >
              Ingest
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Query Form */}
        <div className="bg-slate-800 rounded-lg shadow-lg p-8 mb-8 border border-slate-700">
          <h2 className="text-3xl font-bold text-white mb-6">
            Query NIST Documents
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-slate-300 font-medium mb-2">
                Ask a question about compliance requirements
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., What are the AC-2 access control requirements?"
                  className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold rounded-lg transition-colors"
                >
                  {loading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>
          </form>

          {error && (
            <div className="mt-4 bg-red-900 border border-red-700 rounded-lg p-4 text-red-100">
              {error}
            </div>
          )}
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Generated Answer */}
            <div className="bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-700">
              <h3 className="text-2xl font-bold text-white mb-4">Answer</h3>
              <div className="prose prose-invert max-w-none">
                <p className="text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {result.answer}
                </p>
              </div>
            </div>

            {/* Source Chunks */}
            <div className="bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-700">
              <h3 className="text-2xl font-bold text-white mb-4">
                Source Documents ({result.source_chunks.length})
              </h3>

              <div className="space-y-4">
                {result.source_chunks.map((chunk: SourceChunk, index: number) => (
                  <div
                    key={chunk.chunk_id}
                    className="bg-slate-700 rounded-lg border border-slate-600 overflow-hidden hover:border-blue-500 transition-colors"
                  >
                    {/* Header */}
                    <button
                      onClick={() =>
                        setExpandedChunk(
                          expandedChunk === chunk.chunk_id ? null : chunk.chunk_id
                        )
                      }
                      className="w-full px-6 py-4 flex justify-between items-start hover:bg-slate-600 transition-colors text-left"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="bg-blue-600 text-white text-xs font-semibold px-2 py-1 rounded">
                            {index + 1}
                          </span>
                          <span className="text-slate-300 text-sm">
                            {chunk.source} • Page {chunk.page_number}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-slate-600 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full"
                              style={{
                                width: `${chunk.relevance_score * 100}%`,
                              }}
                            ></div>
                          </div>
                          <span className="text-slate-400 text-sm font-semibold whitespace-nowrap">
                            {(chunk.relevance_score * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <svg
                        className={`w-5 h-5 text-slate-400 transition-transform ml-4 flex-shrink-0 ${
                          expandedChunk === chunk.chunk_id ? 'rotate-180' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 14l-7 7m0 0l-7-7m7 7V3"
                        />
                      </svg>
                    </button>

                    {/* Content */}
                    {expandedChunk === chunk.chunk_id && (
                      <div className="px-6 py-4 bg-slate-600 border-t border-slate-600">
                        <p className="text-slate-200 text-sm leading-relaxed whitespace-pre-wrap">
                          {chunk.text}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {!result && !loading && !error && (
          <div className="bg-slate-800 rounded-lg shadow-lg p-12 border border-slate-700 text-center">
            <svg
              className="mx-auto h-16 w-16 text-slate-600 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12a9 9 0 11-18 0 9 9 0 0118 0m-5.36 4.24l-.707-.707M9 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <p className="text-slate-400 text-lg">
              Enter a query to search NIST compliance documents
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
