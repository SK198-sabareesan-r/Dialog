import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle, AlertTriangle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

let toastId = 0;

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastId;
    setToasts(p => [...p, { id, message, type }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), duration);
  }, []);

  const remove = (id) => setToasts(p => p.filter(t => t.id !== id));

  const styles = {
    success: { bg: '#ECFDF5', border: '#6EE7B7', color: '#065F46', Icon: CheckCircle, iconColor: '#059669' },
    error:   { bg: '#FEF2F2', border: '#FCA5A5', color: '#7F1D1D', Icon: AlertTriangle, iconColor: '#DC2626' },
    info:    { bg: '#EFF6FF', border: '#93C5FD', color: '#1E3A8A', Icon: Info,          iconColor: '#2563EB' },
    warning: { bg: '#FFFBEB', border: '#FCD34D', color: '#78350F', Icon: AlertTriangle, iconColor: '#D97706' },
  };

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      {/* Toast container */}
      <div style={{
        position: 'fixed', bottom: 24, right: 24,
        zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 10,
        maxWidth: 380, width: '100%',
        pointerEvents: 'none',
      }}>
        {toasts.map(t => {
          const s = styles[t.type] || styles.info;
          return (
            <div key={t.id} style={{
              display: 'flex', alignItems: 'flex-start', gap: 12,
              padding: '12px 16px',
              background: s.bg,
              border: `1px solid ${s.border}`,
              borderRadius: 12,
              boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
              pointerEvents: 'all',
              animation: 'toastIn 0.25s ease-out',
            }}>
              <s.Icon style={{ color: s.iconColor, width: 18, height: 18, flexShrink: 0, marginTop: 1 }} />
              <p style={{ color: s.color, fontSize: '0.8125rem', fontWeight: 500, flex: 1, lineHeight: 1.45, fontFamily: 'inherit' }}>
                {t.message}
              </p>
              <button onClick={() => remove(t.id)} style={{ color: s.iconColor, opacity: 0.6, flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginTop: 1 }}>
                <X style={{ width: 14, height: 14 }} />
              </button>
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes toastIn {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside ToastProvider');
  return ctx.toast;
};
