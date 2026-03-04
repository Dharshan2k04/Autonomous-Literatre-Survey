import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listSurveys, deleteSurvey } from '../services/api'
import { clsx } from 'clsx'

const STATUS_COLORS = {
  pending: 'bg-gray-100 text-gray-600',
  querying: 'bg-blue-100 text-blue-700',
  fetching: 'bg-indigo-100 text-indigo-700',
  embedding: 'bg-purple-100 text-purple-700',
  formatting: 'bg-yellow-100 text-yellow-700',
  compiling: 'bg-orange-100 text-orange-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

export default function Home() {
  const [surveys, setSurveys] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () =>
    listSurveys()
      .then(setSurveys)
      .finally(() => setLoading(false))

  useEffect(() => {
    load()
    // Poll for status updates every 5 s
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleDelete = async (id) => {
    if (!confirm('Delete this survey?')) return
    await deleteSurvey(id)
    setSurveys((s) => s.filter((x) => x.id !== id))
  }

  if (loading)
    return <p className="text-gray-500 text-center py-16">Loading surveys…</p>

  if (surveys.length === 0)
    return (
      <div className="text-center py-24">
        <p className="text-5xl mb-4">📚</p>
        <h2 className="text-2xl font-semibold text-gray-700 mb-2">No surveys yet</h2>
        <p className="text-gray-500 mb-6">Create your first literature survey to get started.</p>
        <Link to="/new" className="btn-primary">
          Create Survey
        </Link>
      </div>
    )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Surveys</h1>
        <Link to="/new" className="btn-primary">+ New Survey</Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {surveys.map((s) => (
          <div key={s.id} className="card hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <span className={clsx('badge', STATUS_COLORS[s.status] || 'bg-gray-100')}>
                {s.status}
              </span>
              <button
                onClick={() => handleDelete(s.id)}
                className="text-gray-400 hover:text-red-500 text-sm"
                title="Delete"
              >
                🗑
              </button>
            </div>
            <h3 className="font-semibold text-gray-900 line-clamp-2 mb-2">{s.topic}</h3>
            <p className="text-xs text-gray-400 mb-4">
              {new Date(s.created_at || Date.now()).toLocaleDateString()}
            </p>
            {s.status === 'completed' ? (
              <Link to={`/surveys/${s.id}`} className="btn-primary text-sm w-full text-center block">
                View Survey →
              </Link>
            ) : s.status === 'failed' ? (
              <p className="text-red-500 text-sm">Pipeline failed</p>
            ) : (
              <div className="flex items-center gap-2 text-sm text-blue-600">
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Processing…
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
