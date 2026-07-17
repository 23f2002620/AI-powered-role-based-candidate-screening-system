import { useEffect, useState } from "react";
import { api } from "../api/client";
import Loader from "../components/Loader";

const REC_LABELS = {
  strong_yes: "Strong yes",
  yes: "Yes",
  borderline: "Borderline",
  no: "No",
  insufficient_data: "Insufficient data",
};

export default function SummaryPage({ sessionId, onRestart }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getReport(sessionId).then(setReport).catch((err) => setError(err.message));
  }, [sessionId]);

  return (
    <div className="main">
      <div className="page-header">
        <span className="eyebrow">Step 3 · Session Summary</span>
        <h1 className="page-title">Interview results</h1>
        <p className="page-sub">
          A structured record of the session: what was asked, how it was answered, and where the
          candidate looked strong or thin.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {!report && !error && <Loader label="Compiling final report..." />}

      {report && (
        <>
          <div className="panel">
            <div className="score-hero">
              <div className="score-dial">{report.overall_score ?? "–"}</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>Overall score (0-5 scale)</div>
                <span className={`recommendation-pill rec-${report.recommendation}`}>
                  {REC_LABELS[report.recommendation] || report.recommendation}
                </span>
              </div>
            </div>

            <div className="summary-section">
              <h3>Narrative summary</h3>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: "#333844" }}>{report.summary_text}</p>
            </div>

            <div className="extract-grid">
              <div className="summary-section">
                <h3>Strengths</h3>
                <ul className="bullet-list">
                  {report.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
              <div className="summary-section">
                <h3>Gaps</h3>
                <ul className="bullet-list">
                  {report.gaps.map((g, i) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="summary-section">
              <h3>Topic coverage</h3>
              {Object.entries(report.topic_coverage).map(([topic, score]) => (
                <div className="coverage-bar-row" key={topic}>
                  <div className="cov-topic">{topic}</div>
                  <div className="coverage-bar-track">
                    <div className="coverage-bar-fill" style={{ width: `${(score / 5) * 100}%` }} />
                  </div>
                  <div className="cov-score">{score}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="summary-section transcript-full" style={{ marginTop: 30 }}>
            <h3>Full transcript</h3>
            {report.transcript.map((qa) => (
              <div className="qa-card" key={qa.order_index}>
                <div className="question-meta" style={{ marginBottom: 10 }}>
                  <span className="meta-tag topic">{qa.topic}</span>
                  <span className={`meta-tag difficulty-${qa.difficulty}`}>{qa.difficulty}</span>
                  {qa.quality_score != null && (
                    <span className="meta-tag" style={{ background: "#eef1f5" }}>
                      score {qa.quality_score}
                    </span>
                  )}
                </div>
                <div className="qa-question">{qa.question_text}</div>
                <div className="qa-answer">{qa.answer_text || "(no answer recorded)"}</div>
              </div>
            ))}
          </div>

          <button className="btn btn-ghost" style={{ marginTop: 24 }} onClick={onRestart}>
            ← Start a new screening session
          </button>
        </>
      )}
    </div>
  );
}
