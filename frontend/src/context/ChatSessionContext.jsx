import React, { createContext, useContext, useState, useCallback } from 'react';
import { useAuth } from './AuthContext';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const ChatSessionContext = createContext(null);

export const useChatSessions = () => useContext(ChatSessionContext);

export const ChatSessionProvider = ({ children }) => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    if (!user?.id) return;
    setSessionsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat/sessions?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  }, [user]);

  const createSession = useCallback(async (firstMessage = '') => {
    if (!user?.id) return null;
    try {
      const res = await fetch(`${API_BASE}/api/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id, first_message: firstMessage }),
      });
      if (res.ok) {
        const session = await res.json();
        setSessions(prev => [session, ...prev]);
        setActiveSessionId(session.id);
        return session.id;
      }
    } catch (err) {
      console.error('Failed to create session:', err);
    }
    return null;
  }, [user]);

  const deleteSession = useCallback(async (sessionId) => {
    if (!user?.id) return;
    try {
      await fetch(`${API_BASE}/api/chat/sessions/${sessionId}?user_id=${user.id}`, { method: 'DELETE' });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  }, [user, activeSessionId]);

  const loadSessionMessages = useCallback(async (sessionId) => {
    if (!user?.id) return null;
    try {
      const res = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setActiveSessionId(sessionId);
        return (data.messages || []).map(m => {
          if (m.role === 'user') {
            return {
              role: 'user',
              text: m.content,
              timestamp: m.created_at
            };
          }
          return {
            role: 'assistant',
            answer: m.content,
            citations: m.citations || [],
            language: m.language || {},
            duration: m.duration_ms || 0,
            timestamp: m.created_at
          };
        });
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    }
    return null;
  }, [user]);

  const startNewChat = useCallback(() => {
    setActiveSessionId(null);
  }, []);

  return (
    <ChatSessionContext.Provider value={{
      sessions,
      activeSessionId,
      sessionsLoading,
      loadSessions,
      createSession,
      deleteSession,
      loadSessionMessages,
      startNewChat,
      setActiveSessionId,
    }}>
      {children}
    </ChatSessionContext.Provider>
  );
};
