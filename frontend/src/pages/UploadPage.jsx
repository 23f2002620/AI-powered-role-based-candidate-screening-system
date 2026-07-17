import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function UploadPage({ onCandidateReady }) {
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [candidate, setCandidate] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    api
      .listRoles()
      .then((data) => {
        setRoles(data);
        if (data.length) setSelectedRole(data[0].id);
      })
      .catch((err) => setError(err.message));
  }, []);

  const canSubmit = selectedRole && file && !submitting;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.uploadResume({ file, targetRole: selectedRole, name, email });
      setCandidate(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (candidate) {
    return <ExtractionReview candidate={candidate} onContinue={() => onCandidateReady(candidate)} />;
  }

  return (
    <div className="main">
      <div className="page-header">
        <span className="eyebrow">Step 1 · Candidate Entry</span>
        <h1 className="page-title">Set up the screening session</h1>
        <p className="page-sub">
          Upload a resume and choose the role you're screening for. We'll parse the resume,
          extract skills and technologies, and use them to steer the interview.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <form className="panel" onSubmit={handleSubmit}>
        <div className="field">
          <label>Target role</label>
          <div className="role-grid">
            {roles.map((role) => (
              <button
                type="button"
                key={role.id}
                className={`role-card ${selectedRole === role.id ? "selected" : ""}`}
                onClick={() => setSelectedRole(role.id)}
              >
                <div className="role-label">{role.label}</div>
                <div className="role-hint">Role-specific knowledge base</div>
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Resume (PDF or text)</label>
          <div
            className={`dropzone ${file ? "has-file" : ""}`}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="dz-title">{file ? file.name : "Click to choose a file"}</div>
            <div className="dz-sub">
              {file ? "Click to replace" : "Accepted formats: .pdf, .txt, .md"}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md"
              style={{ display: "none" }}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        <div className="field" style={{ display: "flex", gap: 14 }}>
          <div style={{ flex: 1 }}>
            <label>Name (optional)</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
          </div>
          <div style={{ flex: 1 }}>
            <label>Email (optional)</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="jane@example.com"
            />
          </div>
        </div>

        <button className="btn btn-primary btn-block" type="submit" disabled={!canSubmit}>
          {submitting ? "Parsing resume..." : "Parse resume & continue"}
        </button>
      </form>
    </div>
  );
}

function ExtractionReview({ candidate, onContinue }) {
  const { extracted } = candidate;
  return (
    <div className="main">
      <div className="page-header">
        <span className="eyebrow">Step 1 · Resume Parsed</span>
        <h1 className="page-title">Here's what we picked up</h1>
        <p className="page-sub">
          This extracted profile will shape which topics get asked about and how difficult the
          questions are.
        </p>
      </div>

      <div className="panel">
        <div className="chip-group">
          <span className="chip-group-label">Seniority signal</span>
          <div className="chip-row">
            <span className="chip">{extracted.seniority_signal || "unspecified"}</span>
            {extracted.years_of_experience_estimate != null && (
              <span className="chip">{extracted.years_of_experience_estimate}+ yrs mentioned</span>
            )}
          </div>
        </div>

        <div className="extract-grid" style={{ marginTop: 22 }}>
          <div className="chip-group">
            <span className="chip-group-label">Technologies</span>
            <div className="chip-row">
              {extracted.technologies.length ? (
                extracted.technologies.map((t) => (
                  <span className="chip" key={t}>
                    {t}
                  </span>
                ))
              ) : (
                <span className="chip">none detected</span>
              )}
            </div>
          </div>
          <div className="chip-group">
            <span className="chip-group-label">Skills</span>
            <div className="chip-row">
              {extracted.skills.length ? (
                extracted.skills.map((s) => (
                  <span className="chip" key={s}>
                    {s}
                  </span>
                ))
              ) : (
                <span className="chip">none detected</span>
              )}
            </div>
          </div>
        </div>

        <div className="chip-group" style={{ marginTop: 18 }}>
          <span className="chip-group-label">Domain exposure</span>
          <div className="chip-row">
            {extracted.domain_exposure.length ? (
              extracted.domain_exposure.map((d) => (
                <span className="chip" key={d}>
                  {d}
                </span>
              ))
            ) : (
              <span className="chip">none detected</span>
            )}
          </div>
        </div>

        <button className="btn btn-primary" style={{ marginTop: 26 }} onClick={onContinue}>
          Start the interview →
        </button>
      </div>
    </div>
  );
}
