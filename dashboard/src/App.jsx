import React, { useState, useEffect } from 'react';
import RepoCard from './components/RepoCard';
import RepoDetail from './components/RepoDetail';
import { api } from './api';

// Mock data for when the API is not running
const MOCK_REPOS = [
  { name: 'repo-health-score', owner: 'prachit', grade: 'B', score: 84, last_scanned: new Date().toISOString() },
  { name: 'dotfiles', owner: 'prachit', grade: 'A', score: 92, last_scanned: new Date().toISOString() },
  { name: 'some-other-repo', owner: 'prachit', grade: 'C', score: 71, last_scanned: new Date().toISOString() },
];

const MOCK_HISTORY = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 86400000).toISOString().split('T')[0],
  score: 70 + Math.floor(Math.random() * 25) + (i > 20 ? 5 : 0),
}));

const MOCK_SCORE = {
  score: 84,
  grade: 'B',
  coverage: 78,
  maintainability: 85,
  security: 90,
  documentation: 72,
  activity: 80,
  recommendations: [
    'Add more integration tests to improve coverage',
    'Consider adding a CODEOWNERS file',
    'Improve inline code comments',
  ],
};

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function ErrorMessage({ message, onRetry }) {
  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
      <p className="text-red-400 mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-accent hover:bg-accent/80 text-white rounded-lg transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

export default function App() {
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [repoScore, setRepoScore] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadRepos();
  }, []);

  async function loadRepos() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listRepos();
      setRepos(data);
    } catch (err) {
      console.warn('API unavailable, using mock data:', err.message);
      setRepos(MOCK_REPOS);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectRepo(repo) {
    setSelectedRepo(repo);
    setRepoScore(null);
    setHistory([]);
    try {
      const [score, hist] = await Promise.all([
        api.getRepoScore(repo.owner, repo.name),
        api.getRepoHistory(repo.owner, repo.name),
      ]);
      setRepoScore(score);
      setHistory(hist);
    } catch (err) {
      console.warn('Detail API unavailable, using mock data:', err.message);
      setRepoScore(MOCK_SCORE);
      setHistory(MOCK_HISTORY);
    }
  }

  function handleBack() {
    setSelectedRepo(null);
    setRepoScore(null);
    setHistory([]);
  }

  if (loading) return <LoadingSpinner />;

  if (error) return <ErrorMessage message={error} onRetry={loadRepos} />;

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <header className="border-b border-border bg-bg/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center">
          <span className="text-accent text-xl mr-2">⚡</span>
          <h1 className="text-lg font-bold text-text">Repo Health Score</h1>
          <span className="ml-auto text-muted text-sm hidden sm:block">Powered by repo-health-score</span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {selectedRepo ? (
          <RepoDetail
            repo={selectedRepo}
            score={repoScore}
            history={history}
            onBack={handleBack}
          />
        ) : (
          <>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-text">
                Repositories <span className="text-muted font-normal text-base">({repos.length})</span>
              </h2>
              <button
                onClick={loadRepos}
                className="text-muted hover:text-text text-sm transition-colors flex items-center gap-1"
              >
                ↻ Refresh
              </button>
            </div>

            {repos.length === 0 ? (
              <div className="text-center py-20 text-muted">
                <p className="text-lg mb-2">No repositories scanned yet</p>
                <p className="text-sm">Run a scan to see your repo health scores here</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {repos.map((repo) => (
                  <RepoCard
                    key={`${repo.owner}/${repo.name}`}
                    repo={repo}
                    onClick={() => handleSelectRepo(repo)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}