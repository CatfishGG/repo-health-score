const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  listRepos: () => request('/repos'),
  getRepoScore: (owner, repo) => request(`/repos/${owner}/${repo}/score`),
  getRepoHistory: (owner, repo) => request(`/repos/${owner}/${repo}/history`),
  getBadgeUrl: (owner, repo) => `${API_BASE}/badge/${owner}/${repo}.svg`,
};