import { Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import SurveyDetail from './pages/SurveyDetail'
import NewSurvey from './pages/NewSurvey'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">📚</span>
            <span className="font-bold text-gray-900 text-lg">AutLitSurvey</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-gray-600 hover:text-gray-900 text-sm font-medium">
              My Surveys
            </Link>
            <Link to="/new" className="btn-primary text-sm">
              + New Survey
            </Link>
          </div>
        </div>
      </nav>

      {/* Page content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/new" element={<NewSurvey />} />
          <Route path="/surveys/:id" element={<SurveyDetail />} />
        </Routes>
      </main>

      <footer className="bg-white border-t border-gray-200 py-4 text-center text-xs text-gray-500">
        Autonomous Literature Survey System — powered by GPT-4, LangGraph & Pinecone
      </footer>
    </div>
  )
}
