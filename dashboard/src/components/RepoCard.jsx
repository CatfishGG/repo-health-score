import React from 'react';
import { api } from './api';

const GRADE_COLORS = {
  A: 'text-green-400',
  B: 'text-blue-400',
  C: 'text-yellow-400',
  D: 'text-orange-400',
  F: 'text-red-400',
};

const GRADE_BG = {
  A: 'bg-green-400/10 border-green-400/30',
  B: 'bg-blue-400/10 border-blue-400/30',
  C: 'bg-yellow-400/10 border-yellow-400/30',
  D: 'bg-orange-400/10 border-orange-400/30',
  F: 'bg-red-400/10 border-red-400/30',
};

export default function RepoCard({ repo, onClick }) {
  const grade = repo.grade || 'N/A';
  const score = repo.score ?? '—';

  return (
    <div
      onClick={onClick}
      className={`cursor-pointer rounded-xl border p-5 transition-all duration-200 hover:scale-[1.02] hover:shadow-lg ${GRADE_BG[grade] || 'bg-gray-800/10 border-gray-700/30'}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-text text-lg leading-tight">{repo.name}</h3>
          <p className="text-muted text-sm mt-1">{repo.owner}</p>
          {repo.last_scanned && (
            <p className="text-muted text-xs mt-2">
              Scanned {new Date(repo.last_scanned).toLocaleDateString()}
            </p>
          )}
        </div>
        <div className="flex flex-col items-center">
          <span className={`text-5xl font-bold ${GRADE_COLORS[grade] || 'text-gray-400'}`}>
            {grade}
          </span>
          <span className="text-muted text-sm mt-1">{score}</span>
        </div>
      </div>
    </div>
  );
}