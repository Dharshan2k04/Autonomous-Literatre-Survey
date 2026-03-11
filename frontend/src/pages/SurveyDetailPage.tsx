import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  MessageSquare,
  BookOpen,
  Send,
  ExternalLink,
  Download,
} from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { surveyApi, paperApi, chatApi } from "@/services/endpoints";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { SurveyDetail, Paper, ChatMessage } from "@/types";
import { getStatusColor, getStatusLabel, formatDateTime } from "@/utils";

type Tab = "progress" | "survey" | "papers" | "chat";

export function SurveyDetailPage() {
  const { surveyId } = useParams<{ surveyId: string }>();
  const [survey, setSurvey] = useState<SurveyDetail | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("progress");
  const [loading, setLoading] = useState(true);

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // WebSocket progress
  const { progress } = useWebSocket(
    survey?.status !== "completed" && survey?.status !== "failed" ? surveyId : undefined
  );

  // Load survey data
  useEffect(() => {
    if (!surveyId) return;
    loadSurvey();
  }, [surveyId]);

  // Update survey from WS progress
  useEffect(() => {
    if (progress && survey) {
      setSurvey((prev) =>
        prev
          ? { ...prev, status: progress.status, progress: progress.progress }
          : prev
      );

      if (progress.status === "completed") {
        loadSurvey();
        toast.success("Survey completed!");
      }
      if (progress.status === "failed") {
        toast.error("Survey generation failed");
      }
    }
  }, [progress]);

  // Auto-switch to survey tab when complete
  useEffect(() => {
    if (survey?.status === "completed" && activeTab === "progress") {
      setActiveTab("survey");
    }
  }, [survey?.status]);

  const loadSurvey = useCallback(async () => {
    try {
      const res = await surveyApi.get(surveyId!);
      setSurvey(res.data);
      if (res.data.paper_count > 0) {
        const papersRes = await paperApi.list(surveyId!);
        setPapers(papersRes.data.papers);
      }
    } catch {
      toast.error("Failed to load survey");
    } finally {
      setLoading(false);
    }
  }, [surveyId]);

  const handleChat = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: chatInput.trim(),
      timestamp: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);

    try {
      const res = await chatApi.send(surveyId!, userMsg.content);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.data.answer,
        cited_papers: res.data.cited_papers,
        sources: res.data.sources,
        timestamp: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch {
      toast.error("Chat failed");
    } finally {
      setChatLoading(false);
    }
  };

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleDownloadMd = () => {
    if (!survey?.survey_markdown) return;
    const blob = new Blob([survey.survey_markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `survey-${surveyId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500" />
      </div>
    );
  }

  if (!survey) {
    return <div className="text-center text-dark-400 py-20">Survey not found</div>;
  }

  const tabs: { key: Tab; label: string; icon: JSX.Element }[] = [
    { key: "progress", label: "Progress", icon: <FileText className="h-4 w-4" /> },
    { key: "survey", label: "Survey", icon: <BookOpen className="h-4 w-4" /> },
    { key: "papers", label: `Papers (${papers.length})`, icon: <FileText className="h-4 w-4" /> },
    { key: "chat", label: "Chat", icon: <MessageSquare className="h-4 w-4" /> },
  ];

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <Link to="/surveys" className="text-dark-400 hover:text-dark-200 text-sm flex items-center gap-1 mb-3">
          <ArrowLeft className="h-4 w-4" />
          Back to Surveys
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-dark-50 mb-1">{survey.topic}</h1>
            <div className="flex items-center gap-3 text-sm">
              <span className={getStatusColor(survey.status)}>{getStatusLabel(survey.status)}</span>
              <span className="text-dark-500">{formatDateTime(survey.created_at)}</span>
            </div>
          </div>
          {survey.survey_markdown && (
            <button onClick={handleDownloadMd} className="btn-secondary flex items-center gap-2 text-sm">
              <Download className="h-4 w-4" />
              Download
            </button>
          )}
        </div>

        {/* Progress bar */}
        {survey.status !== "completed" && survey.status !== "failed" && (
          <div className="mt-4">
            <div className="flex justify-between text-xs text-dark-400 mb-1">
              <span>{progress?.message || getStatusLabel(survey.status)}</span>
              <span>{survey.progress}%</span>
            </div>
            <div className="bg-dark-800 rounded-full h-2">
              <div
                className="bg-primary-500 h-2 rounded-full transition-all duration-700"
                style={{ width: `${survey.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-dark-700 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as Tab)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? "border-primary-500 text-primary-400"
                : "border-transparent text-dark-400 hover:text-dark-200"
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "progress" && (
        <div className="card">
          <h3 className="text-lg font-medium text-dark-100 mb-4">Pipeline Progress</h3>
          <div className="space-y-4">
            {[
              { stage: "query_expansion", label: "Query Expansion", desc: "Generating sub-queries" },
              { stage: "paper_retrieval", label: "Paper Retrieval", desc: "Searching databases" },
              { stage: "formatting", label: "Citation Formatting", desc: "Generating IEEE citations" },
              { stage: "survey_generation", label: "Survey Generation", desc: "Compiling survey" },
            ].map((step, idx) => {
              const stageOrder = ["pending", "query_expansion", "paper_retrieval", "formatting", "survey_generation", "completed"];
              const currentIdx = stageOrder.indexOf(survey.status);
              const stepIdx = stageOrder.indexOf(step.stage);
              const isDone = currentIdx > stepIdx || survey.status === "completed";
              const isActive = survey.status === step.stage;

              return (
                <div key={step.stage} className="flex items-center gap-4">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    ${isDone ? "bg-green-500/20 text-green-400" : isActive ? "bg-primary-500/20 text-primary-400 animate-pulse" : "bg-dark-800 text-dark-500"}`}>
                    {isDone ? "✓" : idx + 1}
                  </div>
                  <div>
                    <p className={`text-sm font-medium ${isDone ? "text-green-400" : isActive ? "text-primary-400" : "text-dark-400"}`}>
                      {step.label}
                    </p>
                    <p className="text-xs text-dark-500">{step.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {survey.expanded_queries && (
            <div className="mt-6 pt-6 border-t border-dark-700">
              <h4 className="text-sm font-medium text-dark-200 mb-3">Expanded Queries</h4>
              <div className="space-y-2">
                {(survey.expanded_queries as { sub_queries?: Array<{ query: string; focus: string }> })?.sub_queries?.map((q, i) => (
                    <div key={i} className="bg-dark-800 rounded-lg p-3">
                      <p className="text-sm text-dark-200">{q.query}</p>
                      <span className="text-xs text-primary-400">{q.focus}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {survey.error_message && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{survey.error_message}</p>
            </div>
          )}
        </div>
      )}

      {activeTab === "survey" && (
        <div className="card prose-survey">
          {survey.survey_markdown ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{survey.survey_markdown}</ReactMarkdown>
          ) : (
            <p className="text-dark-400 text-center py-12">
              Survey not yet generated. Check the Progress tab.
            </p>
          )}
        </div>
      )}

      {activeTab === "papers" && (
        <div className="space-y-3">
          {papers.length === 0 ? (
            <div className="card text-center py-12">
              <p className="text-dark-400">No papers retrieved yet.</p>
            </div>
          ) : (
            papers.map((paper) => (
              <div key={paper.id} className="card hover:border-dark-600 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {paper.ieee_number && (
                        <span className="px-2 py-0.5 bg-primary-500/20 text-primary-400 rounded text-xs font-mono">
                          [{paper.ieee_number}]
                        </span>
                      )}
                      <span className="text-xs text-dark-500 capitalize">{paper.source}</span>
                    </div>
                    <h3 className="text-dark-100 font-medium mb-1">{paper.title}</h3>
                    {paper.authors && (
                      <p className="text-xs text-dark-400 mb-2">
                        {paper.authors.slice(0, 5).join(", ")}
                        {paper.authors.length > 5 && " et al."}
                      </p>
                    )}
                    {paper.summary && (
                      <p className="text-sm text-dark-300 mb-2">{paper.summary}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-dark-500">
                      {paper.year && <span>{paper.year}</span>}
                      {paper.venue && <span>{paper.venue}</span>}
                      <span>{paper.citation_count} citations</span>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    {paper.url && (
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-dark-400 hover:text-primary-400 transition-colors"
                        title="View paper"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                  </div>
                </div>
                {paper.ieee_citation && (
                  <div className="mt-3 pt-3 border-t border-dark-800">
                    <p className="text-xs text-dark-400 font-mono">{paper.ieee_citation}</p>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "chat" && (
        <div className="card flex flex-col" style={{ height: "calc(100vh - 320px)" }}>
          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
            {chatMessages.length === 0 && (
              <div className="text-center py-12">
                <MessageSquare className="h-10 w-10 text-dark-600 mx-auto mb-3" />
                <p className="text-dark-400">
                  Ask questions about your paper collection
                </p>
                <p className="text-dark-500 text-xs mt-1">
                  Responses will cite papers by their IEEE numbers
                </p>
              </div>
            )}
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 text-sm ${
                    msg.role === "user"
                      ? "bg-primary-600 text-white"
                      : "bg-dark-800 text-dark-200"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-dark-600">
                      <p className="text-xs text-dark-400 mb-1">Sources:</p>
                      {msg.sources.map((s, i) => (
                        <p key={i} className="text-xs text-dark-500">{s}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-dark-800 rounded-lg px-4 py-3">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-dark-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-dark-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-dark-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat input */}
          <div className="flex gap-3 border-t border-dark-700 pt-4">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleChat()}
              className="input-field flex-1"
              placeholder="Ask about your papers..."
              disabled={chatLoading || survey.status !== "completed"}
            />
            <button
              onClick={handleChat}
              disabled={chatLoading || !chatInput.trim() || survey.status !== "completed"}
              className="btn-primary px-4"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
