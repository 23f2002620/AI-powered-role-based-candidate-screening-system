const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch (_) {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  listRoles: () => request("/api/roles"),

  uploadResume: ({ file, targetRole, name, email }) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_role", targetRole);
    if (name) formData.append("name", name);
    if (email) formData.append("email", email);
    return request("/api/candidates/upload-resume", { method: "POST", body: formData });
  },

  startInterview: (candidateId) =>
    request("/api/interviews/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id: candidateId }),
    }),

  getSession: (sessionId) => request(`/api/interviews/${sessionId}`),

  submitAnswer: (sessionId, questionId, answerText) =>
    request(`/api/interviews/${sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
    }),

  getReport: (sessionId) => request(`/api/interviews/${sessionId}/report`),
};
