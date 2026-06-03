import React, { useState, useRef } from 'react'
import Link from 'next/link'
import { apiClient } from '../lib/api'

export default function IngestPage() {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const file = files[0]

    // Validate file type
    if (!file.name.endsWith('.pdf')) {
      setError('Please upload a PDF file')
      return
    }

    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      const response = await apiClient.ingest(file)
      setMessage(
        `Success! Ingested ${response.chunks_created} chunks from ${file.name}`
      )
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : 'Failed to upload document'
      setError(`Error: ${errorMsg}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      <nav className="bg-slate-950 border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-white">RAG Pipeline</h1>
          <div className="flex gap-6">
            <Link
              href="/"
              className="text-slate-300 hover:text-white transition-colors"
            >
              Query
            </Link>
            <Link
              href="/ingest"
              className="text-blue-400 hover:text-blue-300 transition-colors font-semibold"
            >
              Ingest
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-2xl mx-auto px-4 py-16">
        <div className="bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-700">
          <h2 className="text-3xl font-bold text-white mb-2">
            Ingest Documents
          </h2>
          <p className="text-slate-400 mb-8">
            Upload PDF files to index them for search and retrieval
          </p>

          <div className="space-y-6">
            {/* File Upload Area */}
            <div className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-blue-500 transition-colors">
              <svg
                className="mx-auto h-12 w-12 text-slate-400 mb-4"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20m-4-8l-4-4m0 0l-4 4m4-4v12m-12-4h8"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                disabled={loading}
                className="hidden"
                id="file-upload"
              />

              <label
                htmlFor="file-upload"
                className="cursor-pointer text-slate-300 hover:text-white"
              >
                <span className="text-lg font-semibold">Choose a PDF file</span>
                <p className="text-sm text-slate-400 mt-1">or drag and drop</p>
              </label>
            </div>

            {/* Status Messages */}
            {loading && (
              <div className="bg-blue-900 border border-blue-700 rounded-lg p-4 text-blue-100 flex items-center gap-3">
                <div className="animate-spin h-5 w-5 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                <span>Ingesting document...</span>
              </div>
            )}

            {message && (
              <div className="bg-green-900 border border-green-700 rounded-lg p-4 text-green-100">
                {message}
              </div>
            )}

            {error && (
              <div className="bg-red-900 border border-red-700 rounded-lg p-4 text-red-100">
                {error}
              </div>
            )}
          </div>

          {/* Instructions */}
          <div className="mt-12 bg-slate-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-3">
              Supported Documents
            </h3>
            <ul className="text-slate-300 space-y-2 list-disc list-inside">
              <li>NIST SP 800-53r5 (Recommended)
              </li>
              <li>NIST SP 800-171</li>
              <li>Other NIST compliance documents</li>
              <li>Maximum file size: 50MB</li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  )
}
