import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { getSurvey } from '../services/api'
import { useSurveyChat } from '../hooks/useSurveyChat'

export default function SurveyDetail() {
  const { id } = useParams()
  const [survey, setSurvey] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('survey')
  const [input, setInput] = useState('')
  const chatEndRef = useRef(null)
  const { messages, isConnected, isTyping, sendMessage } = useSurveyChat(Number(id))

  useEffect(() => {
    getSurvey(id)
      .then(setSurvey)
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim()) return
    sendMessage(input.trim())
    setInput('')
  }

  if (loading) return <p className="text-gray-500 text-center py-16">Loading survey…</p>
  if (!survey) return <p className="text-red-500 text-center py-16">Survey not found</p>

  const tabs = [
    { id: 'survey', label: '📄 Survey' },
    { id: 'papers', label: `📑 Papers (${survey.papers?.length || 0})` },
    { id: 'chat', label: '💬 Chat' },
  ]

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link to="/" className="text-gray-400 hover:text-gray-700 text-sm">← Back</Link>
        <h1 className="text-xl font-bold text-gray-900 flex-1 line-clamp-2">{survey.topic}</h1>
      </div>

      {/* Research Gaps */}
      {survey.research_gaps?.length > 0 && (
        <div className="card bg-amber-50 border-amber-200 mb-6">
          <h3 className="font-semibold text-amber-900 mb-2">🔍 Research Gaps</h3>
          <ul className="space-y-1">
            {survey.research_gaps.map((g, i) => (
              <li key={i} className="text-sm text-amber-800">• {g}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-6">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === t.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-900'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Survey tab */}
      {activeTab === 'survey' && (
        <div className="card prose prose-sm max-w-none">
          {survey.survey_markdown ? (
            <ReactMarkdown>{survey.survey_markdown}</ReactMarkdown>
          ) : (
            <p className="text-gray-400">Survey not yet compiled.</p>
          )}
        </div>
      )}

      {/* Papers tab */}
      {activeTab === 'papers' && (
        <div className="space-y-4">
          {(survey.papers || []).map((p) => (
            <div key={p.id} className="card">
              <div className="flex items-start gap-3">
                <span className="text-xs font-bold text-blue-600 bg-blue-50 rounded px-2 py-1 mt-0.5 shrink-0">
                  [{p.ieee_number}]
                </span>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 mb-1">
                    {p.url ? (
                      <a href={p.url} target="_blank" rel="noreferrer" className="hover:text-blue-600">
                        {p.title}
                      </a>
                    ) : p.title}
                  </h3>
                  <p className="text-xs text-gray-500 mb-2">
                    {(p.authors || []).slice(0, 3).join(', ')}
                    {(p.authors?.length || 0) > 3 ? ' et al.' : ''} •{' '}
                    {p.year || 'n.d.'} • {p.venue || 'Unknown venue'}
                  </p>
                  {p.summary && (
                    <p className="text-sm text-gray-600 mb-2">{p.summary}</p>
                  )}
                  {p.cluster_label && (
                    <span className="badge bg-indigo-50 text-indigo-700">
                      {p.cluster_label}
                    </span>
                  )}
                  <p className="text-xs text-gray-400 mt-2">
                    📊 {p.citation_count} citations
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Chat tab */}
      {activeTab === 'chat' && (
        <div className="card flex flex-col" style={{ height: '60vh' }}>
          <div className="flex items-center gap-2 mb-4 pb-4 border-b border-gray-100">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-400'}`} />
            <span className="text-xs text-gray-500">
              {isConnected ? 'Connected — ask anything about your paper collection' : 'Disconnected'}
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {messages.length === 0 && (
              <p className="text-gray-400 text-sm text-center py-8">
                Start a conversation about the papers in this survey.
              </p>
            )}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                    m.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : m.role === 'error'
                      ? 'bg-red-50 text-red-700 border border-red-200'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl px-4 py-2 text-sm text-gray-500 flex gap-1 items-center">
                  <span className="animate-bounce">●</span>
                  <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>●</span>
                  <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>●</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSend} className="mt-4 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about the papers…"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={!isConnected}
            />
            <button
              type="submit"
              className="btn-primary text-sm"
              disabled={!isConnected || !input.trim()}
            >
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
