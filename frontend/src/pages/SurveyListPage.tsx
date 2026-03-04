import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Search, FileText, Trash2, Clock } from "lucide-react";
import { toast } from "sonner";
import { surveyApi } from "@/services/endpoints";
import type { Survey } from "@/types";
import { formatDate, getStatusColor, getStatusLabel, truncate } from "@/utils";

export function SurveyListPage() {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showNewModal, setShowNewModal] = useState(false);
  const [topic, setTopic] = useState("");
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const loadSurveys = async () => {
    try {
      const res = await surveyApi.list();
      setSurveys(res.data.surveys);
      setTotal(res.data.total);
    } catch {
      toast.error("Failed to load surveys");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSurveys();
  }, []);

  const handleCreate = async () => {
    if (!topic.trim() || topic.trim().length < 5) {
      toast.error("Topic must be at least 5 characters");
      return;
    }
    setCreating(true);
    try {
      const res = await surveyApi.create(topic.trim());
      toast.success("Survey created! Agent pipeline started.");
      navigate(`/surveys/${res.data.id}`);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: { message?: string } } } };
      toast.error(error.response?.data?.error?.message || "Failed to create survey");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Delete this survey and all its data?")) return;
    try {
      await surveyApi.delete(id);
      toast.success("Survey deleted");
      loadSurveys();
    } catch {
      toast.error("Failed to delete survey");
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-dark-50">My Surveys</h1>
          <p className="text-dark-400 text-sm mt-1">{total} total surveys</p>
        </div>
        <button onClick={() => setShowNewModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Survey
        </button>
      </div>

      {/* Survey Grid */}
      {surveys.length === 0 ? (
        <div className="card text-center py-16">
          <Search className="h-12 w-12 text-dark-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-dark-200 mb-2">No surveys yet</h3>
          <p className="text-dark-400 mb-6">
            Create your first literature survey to get started
          </p>
          <button onClick={() => setShowNewModal(true)} className="btn-primary">
            Create Survey
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {surveys.map((survey) => (
            <Link
              key={survey.id}
              to={`/surveys/${survey.id}`}
              className="card hover:border-primary-600/50 transition-all duration-200 group"
            >
              <div className="flex items-start justify-between mb-3">
                <FileText className="h-5 w-5 text-primary-500 mt-0.5" />
                <button
                  onClick={(e) => handleDelete(survey.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-dark-500 hover:text-red-400 transition-all"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <h3 className="text-dark-100 font-medium mb-2 line-clamp-2">
                {truncate(survey.topic, 80)}
              </h3>
              <div className="flex items-center gap-2 text-xs mb-2">
                <span className={getStatusColor(survey.status)}>
                  {getStatusLabel(survey.status)}
                </span>
                {survey.status !== "completed" && survey.status !== "failed" && (
                  <div className="flex-1 bg-dark-800 rounded-full h-1.5">
                    <div
                      className="bg-primary-500 h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${survey.progress}%` }}
                    />
                  </div>
                )}
              </div>
              <div className="flex items-center justify-between text-xs text-dark-500">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDate(survey.created_at)}
                </span>
                <span>{survey.paper_count} papers</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* New Survey Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="card max-w-lg w-full animate-slide-up">
            <h2 className="text-xl font-semibold text-dark-50 mb-4">New Literature Survey</h2>
            <p className="text-dark-400 text-sm mb-4">
              Enter a research topic and our AI agents will generate a comprehensive literature survey.
            </p>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="input-field h-32 resize-none mb-4"
              placeholder="e.g., Transformer architectures for natural language processing"
              autoFocus
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => { setShowNewModal(false); setTopic(""); }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || topic.trim().length < 5}
                className="btn-primary"
              >
                {creating ? "Creating..." : "Start Survey"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
