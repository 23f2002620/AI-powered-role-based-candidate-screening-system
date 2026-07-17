import { useEffect, useState } from "react";
import { api } from "../api/client";
import Loader from "../components/Loader";

export default function InterviewPage({ candidate, onComplete }) {
  const [session, setSession] = useState(null);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(true);

  useEffect(() => {
    api
      .startInterview(candidate.id)
      .then(setSession)
      .catch((err) => setError(err.message))
      .finally(() => setStarting(false));
  }, [candidate.id]);

  if (starting) return <MainWrap><Loader label="Starting session and generating your first question..." /></MainWrap>;
  if (error) return <MainWrap><div className="error-banner">{error}</div></MainWrap>;
  if (!session) return null;

  const currentQuestion = session.questions[session.questions.length - 1];
  const answeredCount = session.questions.length - (session.status === "in_progress" ? 1 : 0);
  const total = session.total_questions_planned;
  const progressPct = Math.min(100, (answeredCount / total) * 100);

  async function handleSubmit() {
    if (!answer.trim() || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.submitAnswer(session.id, currentQuestion.id, answer.trim());
      setAnswer("");

      if (result.session_status === "completed" && !result.next_question) {
        onComplete(session.id);
        return;
      }

      // refresh full session so history + new question are in sync
      const refreshed = await api.getSession(session.id);
      setSession(refreshed);

      if (refreshed.status === "completed") {
        onComplete(session.id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const priorQuestions = session.questions.slice(0, -1);

  return (
    <MainWrap>
      <div className="on-air">
        <span className="dot" />
        Live session · question {session.current_question_index} of {total}
      </div>

      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progressPct}%` }} />
      </div>

      <div className="question-meta">
        <span className="meta-tag topic">{currentQuestion.topic}</span>
        <span className={`meta-tag difficulty-${currentQuestion.difficulty}`}>
          {currentQuestion.difficulty}
        </span>
      </div>

      <div className="question-text">{currentQuestion.question_text}</div>

      {error && <div className="error-banner">{error}</div>}

      <textarea
        className="answer-box"
        placeholder="Type your answer here..."
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        disabled={submitting}
      />

      <div className="answer-actions">
        <span className="hint-text">
          {currentQuestion.generation_method === "llm"
            ? "Question generated from your background + retrieved knowledge base context."
            : "Question generated via deterministic template (no LLM key configured)."}
        </span>
        <button className="btn btn-primary" onClick={handleSubmit} disabled={!answer.trim() || submitting}>
          {submitting ? "Evaluating..." : "Submit answer"}
        </button>
      </div>

      {priorQuestions.length > 0 && (
        <div className="transcript-mini">
          <div className="transcript-mini-title">Earlier in this session</div>
          {priorQuestions.map((q) => (
            <div className="transcript-item" key={q.id}>
              <b>{q.topic}:</b> {q.question_text}
            </div>
          ))}
        </div>
      )}
    </MainWrap>
  );
}

function MainWrap({ children }) {
  return (
    <div className="main">
      <div className="page-header">
        <span className="eyebrow">Step 2 · Live Interview</span>
        <h1 className="page-title">Technical screening in progress</h1>
        <p className="page-sub">
          Each question is generated from a retrieved knowledge base passage and your resume
          profile. Difficulty adapts to how you've been answering.
        </p>
      </div>
      {children}
    </div>
  );
}
