import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, FileText, Loader, AlertCircle,
  ChevronDown, ChevronUp, Sparkles, BookOpen, User,
  Globe, Search, Zap, Languages,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useChatSessions } from '../context/ChatSessionContext';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const DIALOG_RED = '#ff4e2e';

// ---------------------------------------------------------------------------
// Markdown renderer — enhanced for chat
// ---------------------------------------------------------------------------
const mdComponents = {
  h1: ({ children }) => (
    <h1 className="text-base font-bold mt-3 mb-2" style={{ color: '#343a40' }}>{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-sm font-bold mt-3 mb-1.5" style={{ color: '#343a40' }}>{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold mt-2 mb-1" style={{ color: '#374151' }}>{children}</h3>
  ),
  p: ({ children }) => (
    <p className="text-sm leading-relaxed mb-2.5 last:mb-0" style={{ color: '#374151' }}>{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-bold" style={{ color: '#343a40' }}>{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic" style={{ color: '#4B5563' }}>{children}</em>
  ),
  ul: ({ children }) => (
    <ul className="list-disc pl-5 space-y-1.5 mb-3 text-sm" style={{ color: '#374151' }}>
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-5 space-y-1.5 mb-3 text-sm" style={{ color: '#374151' }}>
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="text-sm leading-relaxed pl-1" style={{ color: '#374151' }}>{children}</li>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <code className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ background: '#F3F4F6', color: DIALOG_RED }}>
        {children}
      </code>
    ) : (
      <pre className="p-4 rounded-lg text-xs font-mono overflow-x-auto mb-3 leading-relaxed" style={{ background: '#343a40', color: '#E5E7EB' }}>
        <code>{children}</code>
      </pre>
    ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 pl-4 my-3 text-sm" style={{ borderColor: DIALOG_RED, color: '#6B7280', background: '#FFF5F5', padding: '12px 16px', borderRadius: '0 8px 8px 0' }}>
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto mb-3 rounded-lg border" style={{ borderColor: '#E5E7EB' }}>
      <table className="min-w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2.5 text-left text-xs font-semibold border-b" style={{ background: '#F9FAFB', borderColor: '#E5E7EB', color: '#374151' }}>
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 text-xs border-b" style={{ borderColor: '#F3F4F6', color: '#4B5563' }}>
      {children}
    </td>
  ),
  hr: () => <hr className="my-4" style={{ borderColor: '#E8EAF0' }} />,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="underline text-sm font-medium" style={{ color: DIALOG_RED }}>
      {children}
    </a>
  ),
};

// ---------------------------------------------------------------------------
// Progress stages configuration
// ---------------------------------------------------------------------------
const STAGE_CONFIG = {
  detecting_language: { icon: Globe, label: 'Detecting language', color: '#6366F1' },
  language_detected:  { icon: Languages, label: 'Language detected', color: '#059669' },
  translating:        { icon: Languages, label: 'Translating query', color: '#D97706' },
  translated:         { icon: Languages, label: 'Translated', color: '#059669' },
  searching:          { icon: Search, label: 'Searching knowledge base', color: '#3B82F6' },
  generating:         { icon: Zap, label: 'Generating answer', color: '#8B5CF6' },
  streaming:          { icon: Sparkles, label: 'Streaming response', color: DIALOG_RED },
};

// ---------------------------------------------------------------------------
// User message bubble
// ---------------------------------------------------------------------------
const UserBubble = ({ text, picture }) => (
  <div className="flex justify-end mb-5">
    <div className="flex items-end gap-2.5 max-w-[75%]">
      <div className="rounded-2xl rounded-br-md px-4 py-3 shadow-sm" style={{ background: DIALOG_RED }}>
        <p className="text-sm text-white whitespace-pre-wrap leading-relaxed">{text}</p>
      </div>
      {picture ? (
        <div className="flex-shrink-0 w-7 h-7 rounded-full overflow-hidden shadow-sm" style={{ border: '2px solid #F3F4F6' }}>
          <img src={picture} alt="You" className="w-full h-full object-cover" referrerPolicy="no-referrer" />
        </div>
      ) : (
        <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center" style={{ background: `${DIALOG_RED}12` }}>
          <User className="w-3.5 h-3.5" style={{ color: DIALOG_RED }} />
        </div>
      )}
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// AI message bubble (streamed)
// ---------------------------------------------------------------------------
const AiBubble = ({ answer, answerEnglish, language, retrieval, citations, duration }) => {
  const [showEnglish, setShowEnglish] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const isTranslated = language?.detected && language.detected !== 'en';
  const displayAnswer = (isTranslated && showEnglish) ? (answerEnglish || answer) : answer;

  const sourceDocuments = citations
    ? [...new Set(citations.map(c => c.source_file).filter(Boolean))]
    : [];

  return (
    <div className="flex justify-start mb-5">
      <div className="flex items-start gap-2.5 max-w-[85%]">
        <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden mt-1 shadow-sm" style={{ border: '2px solid #F3F4F6' }}>
          <img src="/bot-avatar.png" alt="AI" className="w-full h-full object-cover" />
        </div>
        <div className="space-y-2 min-w-0 flex-1">
          {/* Main answer */}
          <div className="rounded-2xl rounded-tl-md px-5 py-4 shadow-sm" style={{ background: '#FFFFFF', border: '1px solid #E8EAF0' }}>
            {/* Top bar */}
            <div className="flex items-center gap-2 mb-3 pb-2" style={{ borderBottom: '1px solid #F3F4F6' }}>
              <Sparkles className="w-3.5 h-3.5" style={{ color: DIALOG_RED }} />
              <span className="text-xs font-semibold" style={{ color: DIALOG_RED }}>AI Answer</span>
              <div className="ml-auto flex items-center gap-2">
                {duration && (
                  <span className="text-xs" style={{ color: '#C4C9D4' }}>
                    {(duration / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            </div>

            {/* Markdown content */}
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {displayAnswer || ''}
              </ReactMarkdown>
            </div>

            {/* Language badge */}
            {isTranslated && (
              <div className="flex items-center gap-2 mt-3 pt-2" style={{ borderTop: '1px solid #F3F4F6' }}>
                <Globe className="w-3 h-3" style={{ color: '#9CA3AF' }} />
                <span className="text-xs" style={{ color: '#9CA3AF' }}>
                  {showEnglish
                    ? `Original answer in English — query was in ${language.name}`
                    : `Answered in ${language.name} (translated from English)`
                  }
                </span>
                {language.english_query && (
                  <span className="text-xs px-2 py-0.5 rounded" style={{ background: '#F3F4F6', color: '#6B7280' }}>
                    EN: "{language.english_query}"
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Citations — always visible */}
          {citations && citations.length > 0 && (
            <div className="rounded-xl px-4 py-3" style={{ background: '#FAFBFC', border: '1px solid #E8EAF0' }}>
              {/* Header */}
              <div className="flex items-center gap-2 mb-2.5">
                <BookOpen className="w-3.5 h-3.5" style={{ color: '#6B7280' }} />
                <span className="text-xs font-semibold" style={{ color: '#374151' }}>
                  Fetched from {sourceDocuments.length} document{sourceDocuments.length !== 1 ? 's' : ''}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: '#EFF6FF', color: '#3B82F6', border: '1px solid #DBEAFE' }}>
                  {citations.length} chunk{citations.length !== 1 ? 's' : ''} matched
                </span>
              </div>

              {/* Document list — always shown */}
              <div className="space-y-1.5 mb-2">
                {citations.slice(0, showSources ? citations.length : 3).map((chunk, idx) => (
                  <SourceChip key={idx} chunk={chunk} index={idx} />
                ))}
              </div>

              {/* Show more/less toggle if more than 3 */}
              {citations.length > 3 && (
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="flex items-center gap-1 mt-1 text-xs font-medium transition-all"
                  style={{ color: DIALOG_RED }}
                >
                  {showSources ? (
                    <>Show less <ChevronUp className="w-3 h-3" /></>
                  ) : (
                    <>Show {citations.length - 3} more <ChevronDown className="w-3 h-3" /></>
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Source chip — shows where the answer was fetched from
// ---------------------------------------------------------------------------
const SourceChip = ({ chunk, index }) => {
  const [expanded, setExpanded] = useState(false);
  const content = chunk.content?.text || '';
  const truncated = content.length > 200 ? content.substring(0, 200) + '...' : content;
  const scorePercent = chunk.score > 0 ? (chunk.score * 100).toFixed(0) : null;
  const scoreColor = chunk.score > 0.7 ? '#059669' : chunk.score > 0.4 ? '#D97706' : '#9CA3AF';

  return (
    <div className="rounded-lg px-3 py-2.5" style={{ background: '#FFFFFF', border: '1px solid #E8EAF0' }}>
      <div className="flex items-center gap-2">
        <div className="flex-shrink-0 w-5 h-5 rounded flex items-center justify-center" style={{ background: `${DIALOG_RED}08` }}>
          <FileText className="w-3 h-3" style={{ color: DIALOG_RED }} />
        </div>
        <span className="text-xs font-semibold truncate flex-1" style={{ color: '#343a40' }}>
          {chunk.source_file || `Source ${index + 1}`}
        </span>
        {scorePercent && (
          <div className="flex items-center gap-1 flex-shrink-0">
            <div className="w-10 h-1.5 rounded-full overflow-hidden" style={{ background: '#F3F4F6' }}>
              <div className="h-full rounded-full" style={{ width: `${scorePercent}%`, background: scoreColor }} />
            </div>
            <span className="text-xs font-bold" style={{ color: scoreColor }}>
              {scorePercent}%
            </span>
          </div>
        )}
      </div>
      {content && (
        <div className="mt-1.5 ml-7">
          <p className="text-xs leading-relaxed" style={{ color: '#6B7280' }}>
            {expanded ? content : truncated}
          </p>
          {content.length > 200 && (
            <button onClick={() => setExpanded(!expanded)} className="text-xs font-medium mt-1" style={{ color: DIALOG_RED }}>
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Streaming progress indicator
// ---------------------------------------------------------------------------
const StreamingProgress = ({ stages, streamedText }) => {
  return (
    <div className="flex justify-start mb-5">
      <div className="flex items-start gap-2.5 max-w-[85%]">
        <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden mt-1 shadow-sm" style={{ border: '2px solid #F3F4F6' }}>
          <img src="/bot-avatar.png" alt="AI" className="w-full h-full object-cover" />
        </div>
        <div className="space-y-2 min-w-0 flex-1">
          {/* Progress stages */}
          {stages.length > 0 && !streamedText && (
            <div className="rounded-2xl rounded-tl-md px-4 py-3" style={{ background: '#FFFFFF', border: '1px solid #E8EAF0' }}>
              <div className="space-y-2">
                {stages.map((stage, idx) => {
                  const cfg = STAGE_CONFIG[stage.stage] || { icon: Loader, label: stage.message, color: '#6B7280' };
                  const Icon = cfg.icon;
                  const isLatest = idx === stages.length - 1;
                  const isTranslated = stage.stage === 'translated';
                  return (
                    <div key={idx}>
                      <div className="flex items-center gap-2.5">
                        {isLatest ? (
                          <div className="w-5 h-5 flex items-center justify-center">
                            <Icon className="w-4 h-4 animate-pulse" style={{ color: cfg.color }} />
                          </div>
                        ) : (
                          <div className="w-5 h-5 flex items-center justify-center">
                            <div className="w-2 h-2 rounded-full" style={{ background: '#059669' }} />
                          </div>
                        )}
                        <span className="text-xs font-medium" style={{ color: isLatest ? cfg.color : '#9CA3AF' }}>
                          {stage.message}
                        </span>
                      </div>
                      {/* Show translation details */}
                      {isTranslated && stage.translated_query && (
                        <div className="ml-7 mt-1.5 px-3 py-2 rounded-lg" style={{ background: '#F0FDF4', border: '1px solid #D1FAE5' }}>
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="text-xs font-semibold" style={{ color: '#059669' }}>
                              {stage.from_lang} → {stage.to_lang}
                            </span>
                          </div>
                          <p className="text-xs italic" style={{ color: '#065F46' }}>
                            "{stage.translated_query}"
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Streaming text */}
          {streamedText && (
            <div className="rounded-2xl rounded-tl-md px-5 py-4 shadow-sm" style={{ background: '#FFFFFF', border: '1px solid #E8EAF0' }}>
              <div className="flex items-center gap-2 mb-3 pb-2" style={{ borderBottom: '1px solid #F3F4F6' }}>
                <Sparkles className="w-3.5 h-3.5 animate-pulse" style={{ color: DIALOG_RED }} />
                <span className="text-xs font-semibold" style={{ color: DIALOG_RED }}>AI Answer</span>
                <div className="ml-auto">
                  <Loader className="w-3.5 h-3.5 animate-spin" style={{ color: '#C4C9D4' }} />
                </div>
              </div>
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                  {streamedText}
                </ReactMarkdown>
                <span className="inline-block w-2 h-4 ml-0.5 animate-pulse rounded-sm" style={{ background: DIALOG_RED, opacity: 0.6 }} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Error message
// ---------------------------------------------------------------------------
const ErrorBubble = ({ message, onDismiss }) => (
  <div className="flex justify-start mb-5">
    <div className="flex items-start gap-2.5 max-w-[75%]">
      <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center" style={{ background: '#FEF2F2' }}>
        <AlertCircle className="w-3.5 h-3.5" style={{ color: '#DC2626' }} />
      </div>
      <div className="rounded-2xl rounded-tl-md px-4 py-3" style={{ background: '#FEF2F2', border: '1px solid #FECACA' }}>
        <p className="text-sm" style={{ color: '#DC2626' }}>{message}</p>
        <button onClick={onDismiss} className="text-xs mt-1.5 font-medium underline" style={{ color: '#DC2626' }}>Dismiss</button>
      </div>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Welcome screen
// ---------------------------------------------------------------------------
const WelcomeScreen = ({ onSuggestionClick }) => {
  const suggestions = [
    'What policies do we have?',
    'விடுமுறை கொள்கை என்ன?',
    'Show recent reports',
    'නිවාඩු ප්‍රතිපත්තිය',
  ];

  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center max-w-lg px-6">
        <div className="inline-flex p-4 rounded-2xl mb-5 shadow-sm" style={{ background: '#FFF1F3' }}>
          <img src="/bot-avatar.png" alt="AI Assistant" className="w-16 h-16 rounded-full object-cover" />
        </div>
        <h2 className="text-xl font-bold mb-2" style={{ color: '#343a40' }}>
          Knowledge Base Assistant
        </h2>
        <p className="text-sm mb-8 leading-relaxed" style={{ color: '#6B7280' }}>
          Ask questions about your documents in English, Sinhala, or Tamil.<br />
          I'll search your knowledge base and provide answers with cited sources.
        </p>
        <div className="grid grid-cols-2 gap-2">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => onSuggestionClick(q)}
              className="px-4 py-2.5 rounded-xl text-xs font-medium text-left transition-all hover:shadow-sm"
              style={{ background: '#F9FAFB', color: '#4B5563', border: '1px solid #E8EAF0' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = DIALOG_RED; e.currentTarget.style.color = DIALOG_RED; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#E8EAF0'; e.currentTarget.style.color = '#4B5563'; }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Chat Page
// ---------------------------------------------------------------------------
const Retrieve = () => {
  const { user } = useAuth();
  const chatSessions = useChatSessions();
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStages, setStreamStages] = useState([]);
  const [streamedText, setStreamedText] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamStages, streamedText]);

  // When user clicks a session in sidebar, load its messages
  // Skip if we're streaming (session was just created mid-send)
  const prevSessionRef = useRef(null);
  useEffect(() => {
    if (isStreaming) {
      prevSessionRef.current = chatSessions?.activeSessionId || null;
      return;
    }
    if (chatSessions?.activeSessionId && chatSessions.activeSessionId !== prevSessionRef.current) {
      prevSessionRef.current = chatSessions.activeSessionId;
      chatSessions.loadSessionMessages(chatSessions.activeSessionId).then(msgs => {
        if (msgs) setMessages(msgs);
      });
    } else if (!chatSessions?.activeSessionId && prevSessionRef.current) {
      prevSessionRef.current = null;
      setMessages([]);
    }
  }, [chatSessions?.activeSessionId]);

  const handleSend = useCallback(async (overrideQuery) => {
    const trimmed = (overrideQuery || query).trim();
    if (!trimmed || isStreaming) return;

    setMessages(prev => [...prev, { role: 'user', text: trimmed }]);
    setQuery('');
    setIsStreaming(true);
    setStreamStages([]);
    setStreamedText('');

    // Create session if none active
    let sessionId = chatSessions?.activeSessionId;
    if (!sessionId && user?.id && chatSessions) {
      sessionId = await chatSessions.createSession(trimmed);
    }

    let fullAnswer = '';
    let citations = [];
    let language = {};
    let retrieval = {};
    let duration = 0;

    try {
      const body = {
        query: trimmed,
        max_results: 10,
        user_id: user?.id || null,
        session_id: sessionId || null,
      };

      const response = await fetch(`${API_BASE}/api/retrieve/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event = JSON.parse(jsonStr);

            switch (event.type) {
              case 'stage':
                setStreamStages(prev => [...prev, event]);
                break;
              case 'chunk':
                fullAnswer += event.text;
                setStreamedText(fullAnswer);
                break;
              case 'sources':
                citations = event.citations || [];
                break;
              case 'done':
                language = event.language || {};
                retrieval = event.retrieval || {};
                duration = event.duration_ms || 0;
                break;
              case 'error':
                throw new Error(event.message);
              default:
                break;
            }
          } catch (parseErr) {
            if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr;
          }
        }
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        answer: fullAnswer,
        language,
        retrieval,
        citations,
        duration,
      }]);

      // Refresh sessions list in sidebar
      if (chatSessions) chatSessions.loadSessions();

    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'error',
        message: err.message || 'Connection failed. Is the backend running?',
      }]);
    } finally {
      setIsStreaming(false);
      setStreamStages([]);
      setStreamedText('');
      inputRef.current?.focus();
    }
  }, [query, isStreaming, chatSessions, user]);

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isStreaming) {
      e.preventDefault();
      handleSend();
    }
  };

  const dismissError = (idx) => {
    setMessages(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSuggestion = (text) => {
    handleSend(text);
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: '#F8F9FB' }}>
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-6 py-3 bg-white border-b" style={{ borderColor: '#E8EAF0', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg overflow-hidden" style={{ border: '1px solid #F3F4F6' }}>
            <img src="/bot-avatar.png" alt="AI" className="w-full h-full object-cover" />
          </div>
          <div>
            <h1 className="text-sm font-bold" style={{ color: '#343a40' }}>Knowledge Assistant</h1>
            <p className="text-xs" style={{ color: '#9CA3AF' }}>Powered by your knowledge base</p>
          </div>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && !isStreaming && <WelcomeScreen onSuggestionClick={handleSuggestion} />}

          {messages.map((msg, idx) => {
            if (msg.role === 'user') return <UserBubble key={idx} text={msg.text} picture={user?.picture} />;
            if (msg.role === 'assistant') {
              return (
                <AiBubble
                  key={idx}
                  answer={msg.answer}
                  answerEnglish={msg.answerEnglish}
                  language={msg.language}
                  retrieval={msg.retrieval}
                  citations={msg.citations}
                  duration={msg.duration}
                />
              );
            }
            if (msg.role === 'error') {
              return <ErrorBubble key={idx} message={msg.message} onDismiss={() => dismissError(idx)} />;
            }
            return null;
          })}

          {isStreaming && (
            <StreamingProgress stages={streamStages} streamedText={streamedText} />
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 border-t bg-white px-4 md:px-6 py-4" style={{ borderColor: '#E8EAF0' }}>
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="relative flex-1">
              <textarea
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask a question in English, Sinhala, or Tamil..."
                className="w-full px-4 py-3 border rounded-xl resize-none focus:outline-none focus:ring-2 transition-all text-sm leading-relaxed"
                style={{ borderColor: '#E5E7EB', minHeight: '48px', maxHeight: '120px' }}
                rows={1}
                disabled={isStreaming}
                onInput={(e) => {
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                }}
                autoFocus
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={isStreaming || !query.trim()}
              className="flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center transition-all shadow-sm"
              style={{
                background: (isStreaming || !query.trim()) ? '#E5E7EB' : DIALOG_RED,
                cursor: (isStreaming || !query.trim()) ? 'not-allowed' : 'pointer',
              }}
            >
              {isStreaming
                ? <Loader className="w-5 h-5 animate-spin text-white" />
                : <Send className="w-4.5 h-4.5 text-white" />
              }
            </button>
          </div>
          <p className="text-xs mt-2 text-center" style={{ color: '#D1D5DB' }}>
            Answers are generated exclusively from your uploaded documents.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Retrieve;
