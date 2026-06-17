import React, { useState, useCallback } from 'react';
import { Search, FileText, Loader, AlertCircle, Info, Star, Clock, ExternalLink } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v1';
const PINK = '#E91E8C';

const PageHeader = ({ title, subtitle }) => (
  <div
    className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm"
    style={{ borderColor: '#E8EAF0' }}
  >
    <div>
      <h1 className="text-lg font-semibold" style={{ color: '#1A1A2E' }}>{title}</h1>
      {subtitle && <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>{subtitle}</p>}
    </div>
  </div>
);

const ScoreBadge = ({ score }) => {
  const percentage = (score * 100).toFixed(1);
  const color = score > 0.8 ? '#059669' : score > 0.5 ? '#D97706' : '#6B7280';
  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1">
        <Star className="w-3 h-3" style={{ color }} fill={color} />
        <span className="text-xs font-semibold" style={{ color }}>
          {percentage}%
        </span>
      </div>
      <span className="text-xs" style={{ color: '#9CA3AF' }}>relevance</span>
    </div>
  );
};

const ResultCard = ({ result, index }) => {
  const [expanded, setExpanded] = useState(false);
  const content = result.content?.text || 'No content available';
  const location = result.retrievalResultMetadata?.location?.s3Location?.uri || result.location?.s3Location?.uri;
  const metadata = result.metadata || {};
  const score = result.score || 0;

  const truncatedContent = content.length > 200 ? content.substring(0, 200) + '...' : content;
  const displayContent = expanded ? content : truncatedContent;

  return (
    <div
      className="dialog-card p-5 transition-all hover:shadow-lg"
      style={{ borderLeft: `3px solid ${PINK}` }}
    >
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-lg flex-shrink-0" style={{ background: `${PINK}12` }}>
          <FileText className="w-5 h-5" style={{ color: PINK }} />
        </div>
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="flex-1">
              <h3 className="text-sm font-semibold mb-1" style={{ color: '#1A1A2E' }}>
                Result {index + 1}
              </h3>
              {location && (
                <p className="text-xs font-mono break-all" style={{ color: '#6B7280' }}>
                  {location.split('/').pop()}
                </p>
              )}
            </div>
            <ScoreBadge score={score} />
          </div>

          {/* Content */}
          <p className="text-sm leading-relaxed mb-3" style={{ color: '#4B5563' }}>
            {displayContent}
          </p>

          {content.length > 200 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs font-medium mb-3"
              style={{ color: PINK }}
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}

          {/* Metadata */}
          {Object.keys(metadata).length > 0 && (
            <div className="space-y-2 mb-3">
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: '#9CA3AF' }}>
                Metadata
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(metadata).map(([k, v]) => (
                  <span
                    key={k}
                    className="px-2.5 py-1 rounded-md text-xs font-medium"
                    style={{ background: '#F3F4F6', color: '#374151' }}
                  >
                    <span style={{ color: '#9CA3AF' }}>{k}:</span> {v}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Full S3 URI */}
          {location && (
            <div className="pt-3 border-t" style={{ borderColor: '#F3F4F6' }}>
              <a
                href="#"
                onClick={(e) => e.preventDefault()}
                className="flex items-center gap-2 text-xs group"
                style={{ color: '#6B7280' }}
              >
                <ExternalLink className="w-3 h-3 group-hover:text-pink-600" />
                <span className="font-mono break-all group-hover:text-pink-600">{location}</span>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const Retrieve = () => {
  const [query, setQuery] = useState('');
  const [userId, setUserId] = useState('');
  const [teamId, setTeamId] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [searchTime, setSearchTime] = useState(null);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) {
      setError('Please enter a search query.');
      return;
    }
    if (!userId.trim()) {
      setError('User ID is required for access control.');
      return;
    }

    setSearching(true);
    setError(null);
    setResults(null);
    setSearchTime(null);

    const startTime = Date.now();

    try {
      const res = await axios.post(
        `${API_BASE}/retrieve`,
        {
          query: query.trim(),
          user_id: userId.trim(),
          team_id: teamId.trim() || null,
          max_results: maxResults,
        },
        { timeout: 30000 }
      );

      const endTime = Date.now();
      setSearchTime(endTime - startTime);
      setResults(res.data);
    } catch (err) {
      console.error('Search error:', err);
      if (err.code === 'ECONNABORTED') {
        setError('Search timeout. Please try again with a simpler query.');
      } else if (err.response?.status === 403) {
        setError('Access denied. You do not have permission to access these documents.');
      } else {
        setError(err.response?.data?.detail || err.message || 'Search failed. Please try again.');
      }
    } finally {
      setSearching(false);
    }
  }, [query, userId, teamId, maxResults]);

  const onKeyPress = (e) => {
    if (e.key === 'Enter' && !searching) {
      handleSearch();
    }
  };

  return (
    <div className="min-h-screen pb-8">
      <PageHeader
        title="Retrieve Documents"
        subtitle="Search the knowledge base with IAM-based access control"
      />

      <div className="p-6">
        <div className="max-w-5xl mx-auto">
          {/* Info banner */}
          <div className="dialog-card p-4 mb-6" style={{ background: '#EFF6FF', borderColor: '#DBEAFE' }}>
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: '#3B82F6' }} />
              <div className="flex-1">
                <p className="text-xs leading-relaxed" style={{ color: '#1E40AF' }}>
                  Search uses semantic vector similarity with metadata filtering. Results are filtered
                  by User ID and Team ID for secure, role-based access control. Higher scores indicate
                  better relevance.
                </p>
              </div>
            </div>
          </div>

          {/* Search card */}
          <div className="dialog-card p-6 mb-6">
            <div className="space-y-5">
              {/* Query input */}
              <div>
                <label
                  className="block text-xs font-semibold uppercase tracking-wide mb-2"
                  style={{ color: '#6B7280' }}
                >
                  Search Query
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={onKeyPress}
                    placeholder="e.g., What are the best practices for cloud migration?"
                    className="dialog-input pl-11"
                    disabled={searching}
                    aria-label="Search query"
                  />
                  <Search
                    className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: '#C4C9D4' }}
                  />
                </div>
              </div>

              {/* Filters */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label
                    className="block text-xs font-semibold uppercase tracking-wide mb-2"
                    style={{ color: '#6B7280' }}
                  >
                    User ID <span style={{ color: PINK }}>*</span>
                  </label>
                  <input
                    type="text"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="e.g., user123"
                    className="dialog-input"
                    disabled={searching}
                    aria-label="User ID"
                  />
                </div>
                <div>
                  <label
                    className="block text-xs font-semibold uppercase tracking-wide mb-2"
                    style={{ color: '#6B7280' }}
                  >
                    Team ID{' '}
                    <span style={{ color: '#C4C9D4', fontWeight: 400, textTransform: 'none' }}>
                      (optional)
                    </span>
                  </label>
                  <input
                    type="text"
                    value={teamId}
                    onChange={(e) => setTeamId(e.target.value)}
                    placeholder="e.g., team456"
                    className="dialog-input"
                    disabled={searching}
                    aria-label="Team ID"
                  />
                </div>
                <div>
                  <label
                    className="block text-xs font-semibold uppercase tracking-wide mb-2"
                    style={{ color: '#6B7280' }}
                  >
                    Max Results
                  </label>
                  <input
                    type="number"
                    value={maxResults}
                    onChange={(e) => setMaxResults(parseInt(e.target.value) || 10)}
                    min="1"
                    max="50"
                    className="dialog-input"
                    disabled={searching}
                    aria-label="Maximum results"
                  />
                </div>
              </div>

              {/* Search button */}
              <button
                onClick={handleSearch}
                disabled={searching || !query.trim() || !userId.trim()}
                className="btn-dialog w-full py-3.5 text-base"
                aria-label="Search knowledge base"
              >
                {searching ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="w-5 h-5" />
                    Search Knowledge Base
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <div
              className="dialog-card p-5 mb-6 animate-in"
              style={{ borderLeft: '4px solid #DC2626' }}
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 flex-shrink-0 mt-0.5" style={{ color: '#DC2626' }} />
                <div className="flex-1">
                  <h3 className="font-semibold text-base mb-1" style={{ color: '#1A1A2E' }}>
                    Search Failed
                  </h3>
                  <p className="text-sm" style={{ color: '#6B7280' }}>
                    {error}
                  </p>
                  <button
                    onClick={() => setError(null)}
                    className="mt-3 text-xs font-medium underline"
                    style={{ color: '#DC2626' }}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {results && (
            <div>
              {/* Results header */}
              <div className="dialog-card p-5 mb-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold" style={{ color: '#1A1A2E' }}>
                      Search Results
                    </h2>
                    <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>
                      Found {results.results_count} result{results.results_count !== 1 ? 's' : ''}{' '}
                      for "{results.query}"
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    {searchTime && (
                      <div className="flex items-center gap-2 text-xs" style={{ color: '#6B7280' }}>
                        <Clock className="w-4 h-4" />
                        <span>{(searchTime / 1000).toFixed(2)}s</span>
                      </div>
                    )}
                    <span className="badge-pink">
                      {results.results_count} result{results.results_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
              </div>

              {/* Results list */}
              {results.results_count > 0 ? (
                <div className="space-y-4">
                  {results.results.map((result, idx) => (
                    <ResultCard key={idx} result={result} index={idx} />
                  ))}
                </div>
              ) : (
                <div className="dialog-card p-12 text-center">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" style={{ color: '#9CA3AF' }} />
                  <h3 className="text-base font-semibold mb-2" style={{ color: '#1A1A2E' }}>
                    No results found
                  </h3>
                  <p className="text-sm mb-4" style={{ color: '#6B7280' }}>
                    Try adjusting your query or check your access permissions
                  </p>
                  <div className="text-xs space-y-1" style={{ color: '#9CA3AF' }}>
                    <p>• Use more specific keywords</p>
                    <p>• Check if documents are accessible to your User/Team ID</p>
                    <p>• Try increasing the max results</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Retrieve;
