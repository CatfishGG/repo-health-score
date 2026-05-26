import React from 'react';
import ScoreChart from './ScoreChart';
import Badge from './Badge';

const GRADE_COLORS = {
  A: 'text-green-400',
  B: 'text-blue-400',
  C: 'text-yellow-400',
  D: 'text-orange-400',
  F: 'text-red-400',
};

const DIMENSION_LABELS = {
  coverage: 'Test Coverage',
  maintainability: 'Maintainability',
  security: 'Security',
  documentation: 'Documentation',
  activity: 'Activity',
  responsiveness: 'Responsiveness',
  license: 'License',
  stars: 'Stars',
  forks: 'Forks',
  open_issues: 'Open Issues',
  closed_issues: 'Closed Issues',
  pr_merge_time: 'PR Merge Time',
  commit_frequency: 'Commit Frequency',
};

function DimensionBar({ label, value, max = 100 }) {
  const pct = Math.min(100, Math.max(0, value));
  const color =
    pct >= 80 ? 'bg-green-400' : pct >= 60 ? 'bg-blue-400' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-muted">{DIMENSION_LABELS[label] || label}</span>
        <span className="text-text font-medium">{value}</span>
      </div>
      <div className="h-2 bg-surface rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RepoDetail({ repo, score, history, onBack }) {
  if (!repo) return null;

  const grade = score?.grade || 'N/A';
  const numericScore = score?.score ?? '—';

  // Parse dimensions from score object
  const dimensions = score
    ? Object.entries(score)
        .filter(([k, v]) => typeof v === 'number' && !['score', 'grade'].includes(k))
        .map(([k, v]) => [k, v])
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="text-muted hover:text-text transition-colors text-sm flex items-center gap-1"
        >
          ← Back
        </button>
        <div className="flex-1">
          <h2 className="text-xl font-semibold text-text">{repo.name}</h2>
          <p className="text-muted text-sm">{repo.owner}</p>
        </div>
        <div className="text-center">
          <span className={`text-6xl font-bold block ${GRADE_COLORS[grade] || 'text-gray-400'}`}>
            {grade}
          </span>
          <span className="text-muted text-sm">Score {numericScore}</span>
        </div>
      </div>

      {/* Score Breakdown */}
      {dimensions.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="text-sm font-medium text-text mb-4">Score Breakdown</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {dimensions.map(([key, val]) => (
              <DimensionBar key={key} label={key} value={val} />
            ))}
          </div>
        </div>
      )}

      {/* Score History */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="text-sm font-medium text-text mb-4">Score History (Last 30 Days)</h3>
        <ScoreChart history={history} />
      </div>

      {/* Badge */}
      <Badge owner={repo.owner} repo={repo.name} />

      {/* Recommendations */}
      {score?.recommendations && score.recommendations.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="text-sm font-medium text-text mb-3">Recommendations</h3>
          <ul className="space-y-2">
            {score.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted">
                <span className="text-accent mt-0.5">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}