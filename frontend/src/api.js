async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, options);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export const api = {
  health: () => request("/health"),
  startInterview: (formData) => request("/interviews", { method: "POST", body: formData }),
  listInterviews: () => request("/interviews"),
  getInterview: (id) => request(`/interviews/${id}`),
  deleteInterview: (id) => request(`/interviews/${id}`, { method: "DELETE" }),
  submitAnswer: (sid, qid, answer, timeSeconds) =>
    request(`/interviews/${sid}/questions/${qid}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer, time_seconds: timeSeconds }),
    }),
  hint: (sid, qid) => request(`/interviews/${sid}/questions/${qid}/hint`, { method: "POST" }),
  followup: (sid, qid) => request(`/interviews/${sid}/questions/${qid}/followup`, { method: "POST" }),
  complete: (id) => request(`/interviews/${id}/complete`, { method: "POST" }),
  stats: () => request("/stats"),
};
