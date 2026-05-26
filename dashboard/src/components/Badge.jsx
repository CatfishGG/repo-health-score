import React from 'react';
import { api } from './api';

export default function Badge({ owner, repo }) {
  const badgeUrl = api.getBadgeUrl(owner, repo);
  const markdown = `[![Repo Health](${badgeUrl})](https://github.com/${owner}/${repo})`;

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown).catch(() => {});
  };

  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <h4 className="text-sm font-medium text-text mb-3">Badge</h4>
      <div className="flex items-center gap-4">
        <img
          src={badgeUrl}
          alt={`${owner}/${repo} health badge`}
          className="h-8 rounded"
          onError={(e) => { e.target.style.display = 'none'; }}
        />
        <div className="flex-1">
          <p className="text-xs text-muted font-mono break-all">{markdown}</p>
        </div>
        <button
          onClick={handleCopy}
          className="px-3 py-1.5 bg-accent hover:bg-accent/80 text-white text-sm rounded-lg transition-colors whitespace-nowrap"
        >
          Copy MD
        </button>
      </div>
    </div>
  );
}