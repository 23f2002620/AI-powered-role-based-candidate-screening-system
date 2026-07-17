import { useState } from "react";
import Sidebar from "./components/Sidebar";
import UploadPage from "./pages/UploadPage";
import InterviewPage from "./pages/InterviewPage";
import SummaryPage from "./pages/SummaryPage";

export default function App() {
  const [stage, setStage] = useState("setup"); // setup | interview | summary
  const [candidate, setCandidate] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  function handleCandidateReady(c) {
    setCandidate(c);
    setStage("interview");
  }

  function handleInterviewComplete(sid) {
    setSessionId(sid);
    setStage("summary");
  }

  function handleRestart() {
    setCandidate(null);
    setSessionId(null);
    setStage("setup");
  }

  return (
    <div className="app-shell">
      <Sidebar stage={stage} />
      {stage === "setup" && <UploadPage onCandidateReady={handleCandidateReady} />}
      {stage === "interview" && candidate && (
        <InterviewPage candidate={candidate} onComplete={handleInterviewComplete} />
      )}
      {stage === "summary" && sessionId && (
        <SummaryPage sessionId={sessionId} onRestart={handleRestart} />
      )}
    </div>
  );
}
