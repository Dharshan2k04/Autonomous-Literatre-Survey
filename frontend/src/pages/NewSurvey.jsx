import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createSurvey } from '../services/api'

export default function NewSurvey() {
  const navigate = useNavigate()
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!topic.trim()) return
    setLoading(true)
    setError('')
    try {
      const survey = await createSurvey(topic.trim())
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create survey')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">New Literature Survey</h1>
      <p className="text-gray-500 mb-8">
        Enter a research topic and our AI agents will automatically retrieve, analyze,
        and compile a structured literature survey with IEEE citations.
      </p>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Research Topic
            </label>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Transformer models for protein structure prediction"
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         resize-none"
              maxLength={512}
            />
            <p className="text-xs text-gray-400 mt-1">{topic.length}/512 characters</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button type="submit" className="btn-primary" disabled={loading || !topic.trim()}>
              {loading ? 'Submitting…' : '🚀 Generate Survey'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/')}
            >
              Cancel
            </button>
          </div>
        </form>

        <div className="mt-8 border-t border-gray-100 pt-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">How it works</h3>
          <ol className="space-y-2 text-sm text-gray-500">
            <li>1️⃣ <strong>Query Strategist</strong> — GPT-4 expands your topic into 3 targeted sub-queries</li>
            <li>2️⃣ <strong>Citation Explorer</strong> — Fetches papers from Semantic Scholar, arXiv & Crossref in parallel</li>
            <li>3️⃣ <strong>IEEE Formatter</strong> — Generates proper IEEE citations and contextual summaries</li>
            <li>4️⃣ <strong>Survey Architect</strong> — Clusters papers, identifies research gaps, compiles full survey</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
