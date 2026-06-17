import React, { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Search, FileText, Loader, AlertCircle, Star, Clock,
  ChevronDown, ChevronUp, Sparkles, BookOpen,
} from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';
const DIALOG_RED = '#E4002B';

// ---------------------------------------------------------------------------
// Markdown renderer — maps markdown elements to styled HTML
// ---------------------------------------------------------------------------
const mdComponents = {
  h1: ({ children }) => (
    <h1 className="text-base font-bold mt-4 mb-2" style={{ color: '#1A1A2E' }}>{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-sm font-bold mt-3 mb-1.5" style={{ color: '#1A1A2E' }}>{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold mt-2 mb-1" style={{ color: '#374151' }}>{children}</h3>
  ),
  p: ({ children }) => (
    <p className="text-sm leading-relaxed mb-2 last:mb-0" style={{ color: '#374151' }}>{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold" style={{ color: '#1A1A2E' }}>{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic" style={{ color: '#374151' }}>{children}</em>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-inside space-y-1 mb-2 text-sm" style={{ color: '#374151' }}>
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside space-y-1 mb-2 text-sm" style={{ color: '#374151' }}>
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="text-sm leading-relaxed" style={{ color: '#374151' }}>{children}</li>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <code
        className="px-1.5 py-0.5 rounded text-xs font-mono"
        style={{ background: '#F3F4F6', color: DIALOG_RED }}
      >
        {children}
      </code>
    ) : (
      <pre
        className="p-3 rounded-lg text-xs font-mono overflow-x-auto mb-2"
        style={{ background: '#1A1A2E', color: '#E5E7EB' }}
      >
        <code>{children}</code>
      </pre>
    ),
  blockquote: ({ children }) => (
    <blockquote
      className="border-l-4 pl-3 my-2 text-sm italic"
      style={{ borderColor: DIALOG_RED, color: '#6B7280' }}
    >
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto mb-2">
      <table className="min-w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th
      className="px-3 py-2 text-left text-xs font-semibold border"
      style={{ background: '#F3F4F6', borderColor: '#E5E7EB', color: '#374151' }}
    >
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td
      className="px-3 py-2 text-xs border"
      style={{ borderColor: '#E5E7EB', color: '#4B5563' }}
    >
      {children}
    </td>
  ),
  hr: () => <hr className="my-3" style={{ borderColor: '#E5E7EB' }} />,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline text-sm"
      style={{ color: DIALOG_RED }}
    >
      {children}
    </a>
  ),
};

// ---------------------------------------------------------------------------
// Page header
// ---------------------------------------------------------------------------
const PageHeader = ({ title, subtitle }) => (
  <div
    className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm"
    style={{ borderColor: '#E8EAF0' }}
  >
    <div>
      <h1 className="text-xl font-semibold" style={{ color: '#1F2937' }}>{title}</h1>
      {subtitle && <p className="text-sm mt-0.5" style={{ color: '#9CA3AF' }}>{subtitle}</p>}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Score badge (for cited chunks)
// ---------------------------------------------------------------------------
const ScoreBadge = ({ score }) => {
  if (!score || score === 0) return null;
  const percentage = (score * 100).toFixed(1);
  const color = score > 0.8 ? '#059669' : score > 0.5 ? '#D97706' : '#6B7280';
  return (
    <div className="flex items-center gap-1.5">
      <Star className="w-3 h-3" style={{ color }} fill={color} />
      <span className="text-xs font-semibold" style={{ color }}>{percentage}%</span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// AI Answer card — renders markdown, with language toggle for translations
// ---------------------------------------------------------------------------
const AnswerCard = ({ answer, answerEnglish, retrieval, language, citations }) => {
  const [showEnglish, setShowEnglish] = useState(false);
  const isTranslated = language?.detected && language.detected !== 'en';
  const displayAnswer = (isTranslated && showEnglish) ? answerEnglish : answer;

  // Extract unique source documents
  const sourceDocuments = citations
    ? [...new Set(citations.map(c => c.source_file).filter(Boolean))]
    : [];

  return (
    <div
      className="bg-white rounded-xl shadow-sm p-5 mb-4"
      style={{ borderLeft: `4px solid ${DIALOG_RED}`, background: '#FFF5F5' }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 flex-shrink-0" style={{ color: DIALOG_RED }} />
        <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: DIALOG_RED }}>
          AI Answer
        </span>
        <div className="ml-auto flex items-center gap-2">
          {isTranslated && answerEnglish && (
            <button
              onClick={() => setShowEnglish(!showEnglish)}
              className="text-xs px-2 py-0.5 rounded-full font-medium transition-colors"
              style={{
                background: showEnglish ? '#F3F4F6' : `${DIALOG_RED}18`,
                color: showEnglish ? '#6B7280' : DIALOG_RED,
                border: `1px solid ${showEnglish ? '#E5E7EB' : `${DIALOG_RED}40`}`,
              }}
            >
              {showEnglish ? `Show ${language.name}` : 'Show English'}
            </button>
          )}
          {retrieval && (
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ background: '#F3F4F6', color: '#6B7280' }}
            >
              {retrieval.search_type}
              {retrieval.chunks_returned > 0 && ` · ${retrieval.chunks_returned} sources`}
            </span>
          )}
        </div>
      </div>

      {/* Rendered markdown */}
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
          {displayAnswer}
        </ReactMarkdown>
      </div>

      {/* Citations - Show source documents */}
      {sourceDocuments.length > 0 && (
        <div className="mt-4 pt-4 border-t" style={{ borderColor: '#F3F4F6' }}>
          <div className="flex items-start gap-2">
            <FileText className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: '#9CA3AF' }} />
            <div className="flex-1">
              <p className="text-xs font-medium mb-1.5" style={{ color: '#6B7280' }}>
                Sources cited:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {sourceDocuments.map((doc, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium"
                    style={{
                      background: '#F9FAFB',
                      border: '1px solid #E5E7EB',
                      color: '#374151'
                    }}
                  >
                    <span className="font-semibold" style={{ color: DIALOG_RED }}>[{idx + 1}]</span>
                    {doc}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Language note */}
      {isTranslated && !showEnglish && (
        <p className="text-xs mt-3 pt-3 border-t" style={{ borderColor: '#F3F4F6', color: '#9CA3AF' }}>
          Detected language: {language.name} — answer translated from English
        </p>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Single cited chunk card
// ---------------------------------------------------------------------------
const ResultCard = ({ result, index }) => {
  const [expanded, setExpanded] = useState(false);
  const content = result.content?.text || result.content || '';
  const location = result.location?.s3Location?.uri || result.s3_uri || '';
  const metadata = result.metadata || {};
  const score = result.score || 0;

  const truncatedContent = content.length > 280 ? content.substring(0, 280) + '…' : content;
  const displayContent = expanded ? content : truncatedContent;

  const displayMetadata = Object.entries(metadata).filter(
    ([k]) => !['x-amz-bedrock-kb-source-uri', 'x-amz-bedrock-kb-chunk-id'].includes(k)
  );

  return (
    <div
      className="rounded-lg p-4 transition-all"
      style={{ background: '#F9FAFB', border: '1px solid #E5E7EB' }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-3.5 h-3.5 flex-shrink-0" style={{ color: '#9CA3AF' }} />
          <span className="text-xs font-medium truncate" style={{ color: '#6B7280' }}>
            {result.source_file || location.split('/').pop() || `Source ${index + 1}`}
          </span>
        </div>
        <ScoreBadge score={score} />
      </div>

      {content && (
        <>
          <p className="text-xs leading-relaxed" style={{ color: '#4B5563' }}>
            {displayContent}
          </p>
          {content.length > 280 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs font-medium mt-1.5"
              style={{ color: DIALOG_RED }}
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </>
      )}

      {displayMetadata.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {displayMetadata.slice(0, 4).map(([k, v]) => (
            <span
              key={k}
              className="px-1.5 py-0.5 rounded text-xs"
              style={{ background: '#E5E7EB', color: '#6B7280' }}
            >
              {k}: {String(v).substring(0, 40)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Collapsible cited sources — only rendered when chunks > 0
// ---------------------------------------------------------------------------
const CitedChunks = ({ results }) => {
  const [open, setOpen] = useState(false);
  if (!results || results.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3 text-left"
        style={{ borderBottom: open ? '1px solid #F3F4F6' : 'none' }}
      >
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4" style={{ color: '#6B7280' }} />
          <span className="text-sm font-medium" style={{ color: '#374151' }}>
            Source chunks
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ background: '#F3F4F6', color: '#6B7280' }}
          >
            {results.length}
          </span>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4" style={{ color: '#9CA3AF' }} />
          : <ChevronDown className="w-4 h-4" style={{ color: '#9CA3AF' }} />
        }
      </button>
      {open && (
        <div className="p-4 space-y-2">
          {results.map((result, idx) => (
            <ResultCard key={idx} result={result} index={idx} />
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
const Retrieve = () => {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [searchTime, setSearchTime] = useState(null);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;

    setSearching(true);
    setError(null);
    setResults(null);
    setSearchTime(null);

    const startTime = Date.now();

    try {
      const res = await axios.post(
        `${API_BASE}/retrieve`,
        { query: query.trim(), max_results: 10 },
        { timeout: 30000 }
      );
      setSearchTime(Date.now() - startTime);
      setResults(res.data);
    } catch (err) {
      console.error('Search error:', err);
      setError(
        err.code === 'ECONNABORTED'
          ? 'Search timed out. Please try again.'
          : err.response?.data?.detail || err.message || 'Search failed. Please try again.'
      );
    } finally {
      setSearching(false);
    }
  }, [query]);

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !searching) handleSearch();
  };

  const hasAnswer  = results?.answer;
  const hasChunks  = results?.results?.length > 0;
  const noContent  = results && !hasAnswer && !hasChunks;

  return (
    <div className="min-h-screen bg-gray-50 pb-8">
      <PageHeader
        title="Retrieve Documents"
        subtitle="Ask anything — hybrid search with AI-generated answers"
      />

      <div className="p-6">
        <div className="max-w-4xl mx-auto">

          {/* ── Search bar ─────────────────────────────────────────────── */}
          <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 pointer-events-none"
                  style={{ color: '#9CA3AF', zIndex: 1 }}
                />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Ask a question or search for documents..."
                  className="w-full px-4 py-3 pl-11 border rounded-lg focus:outline-none focus:ring-2 transition-all"
                  style={{
                    borderColor: '#E5E7EB',
                    focusRingColor: DIALOG_RED
                  }}
                  disabled={searching}
                  aria-label="Search query"
                  autoFocus
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={searching || !query.trim()}
                className="px-6 py-3 rounded-lg font-semibold text-white flex items-center gap-2 transition-all"
                style={{
                  background: (searching || !query.trim()) ? '#CBD5E0' : DIALOG_RED,
                  cursor: (searching || !query.trim()) ? 'not-allowed' : 'pointer'
                }}
                aria-label="Search knowledge base"
              >
                {searching
                  ? <Loader className="w-5 h-5 animate-spin" />
                  : <><Search className="w-5 h-5" />Search</>
                }
              </button>
            </div>
          </div>

          {/* ── Error ──────────────────────────────────────────────────── */}
          {error && (
            <div
              className="bg-white rounded-xl shadow-sm p-4 mb-6 flex items-start gap-3"
              style={{ borderLeft: '4px solid #DC2626' }}
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: '#DC2626' }} />
              <div className="flex-1">
                <p className="text-sm font-semibold mb-0.5" style={{ color: '#1A1A2E' }}>Search failed</p>
                <p className="text-sm" style={{ color: '#6B7280' }}>{error}</p>
              </div>
              <button onClick={() => setError(null)} className="text-xs underline" style={{ color: '#DC2626' }}>
                Dismiss
              </button>
            </div>
          )}

          {/* ── Results ────────────────────────────────────────────────── */}
          {results && (
            <>
              {/* Meta bar */}
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm" style={{ color: '#6B7280' }}>
                  Results for{' '}
                  <span className="font-medium" style={{ color: '#1A1A2E' }}>"{results.query}"</span>
                  {hasChunks && (
                    <span className="ml-2 text-xs" style={{ color: '#9CA3AF' }}>
                      · {results.results.length} source{results.results.length !== 1 ? 's' : ''} cited
                    </span>
                  )}
                </p>
                {searchTime && (
                  <div className="flex items-center gap-1.5 text-xs" style={{ color: '#9CA3AF' }}>
                    <Clock className="w-3.5 h-3.5" />
                    {(searchTime / 1000).toFixed(2)}s
                  </div>
                )}
              </div>

              {/* AI answer with markdown */}
              {hasAnswer && (
                <AnswerCard
                  answer={results.answer}
                  answerEnglish={results.answer_english}
                  retrieval={results.retrieval}
                  language={results.language}
                  citations={results.results}
                />
              )}

              {/* Cited source chunks — hidden when empty */}
              {hasChunks && <CitedChunks results={results.results} />}

              {/* Only show "no results" when there is truly nothing at all */}
              {noContent && (
                <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                  <FileText className="w-10 h-10 mx-auto mb-4 opacity-20" style={{ color: '#9CA3AF' }} />
                  <p className="text-sm font-semibold mb-1" style={{ color: '#1A1A2E' }}>No results found</p>
                  <p className="text-xs" style={{ color: '#9CA3AF' }}>
                    Try different keywords or check that documents have been uploaded and ingested.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Retrieve;
