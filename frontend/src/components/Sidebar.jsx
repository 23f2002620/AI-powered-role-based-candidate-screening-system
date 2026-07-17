const STEPS = [
  { key: "setup", title: "Candidate Entry", desc: "Upload resume & pick a role" },
  { key: "interview", title: "Live Interview", desc: "Adaptive, context-grounded Q&A" },
  { key: "summary", title: "Session Summary", desc: "Structured results & insights" },
];

export default function Sidebar({ stage }) {
  const activeIndex = STEPS.findIndex((s) => s.key === stage);

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">Screening&nbsp;Room</span>
      </div>
      <span className="brand-tag" style={{ marginTop: -26 }}>
        RAG-grounded interview engine
      </span>

      <nav className="step-rail">
        {STEPS.map((step, i) => (
          <div
            key={step.key}
            className={`step-item ${i === activeIndex ? "active" : ""} ${
              i < activeIndex ? "done" : ""
            }`}
          >
            <div className="step-index">{i < activeIndex ? "✓" : i + 1}</div>
            <div className="step-copy">
              <div className="step-title">{step.title}</div>
              <div className="step-desc">{step.desc}</div>
            </div>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        candidate → resume parse
        <br />
        → context construction
        <br />
        → RAG retrieval → question
      </div>
    </aside>
  );
}
