import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Loader } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';

/* ── Dialog logo — matches dialog.lk branding ── */
const DialogLogo = ({ size = 120 }) => (
  <svg width={size} height={size * 0.45} viewBox="0 0 200 80" fill="none" xmlns="http://www.w3.org/2000/svg">
    {/* Arrow/play mark */}
    <polygon points="8,8 8,52 44,30" fill="#F7941D" />
    <polygon points="24,18 24,52 52,35" fill="#ED1C24" opacity="0.85" />
    {/* "Dialog" text */}
    <text x="60" y="52" fontFamily="Arial, sans-serif" fontWeight="700" fontSize="40" fill="#ED1C24" letterSpacing="-1">
      Dialog
    </text>
  </svg>
);

/* ── Animated wave background — Dialog.lk brand gradient ── */
const WaveBackground = () => (
  <div style={{
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    zIndex: 0, overflow: 'hidden',
    background: '#ffffff',
  }}>
    {/* Top wave layer */}
    <svg
      viewBox="0 0 1440 320"
      preserveAspectRatio="none"
      style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '55%' }}
    >
      <defs>
        <linearGradient id="wave1" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#f36d24" stopOpacity="0.9" />
          <stop offset="50%"  stopColor="#e34984" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#9e3883" stopOpacity="0.8" />
        </linearGradient>
        <linearGradient id="wave2" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#f7941d" stopOpacity="0.6" />
          <stop offset="50%"  stopColor="#ff4e2e" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#9F215D" stopOpacity="0.4" />
        </linearGradient>
      </defs>
      {/* Back wave */}
      <path
        d="M0,0 L0,180 C180,260 360,300 540,240 C720,180 900,80 1080,100 C1260,120 1380,200 1440,220 L1440,0 Z"
        fill="url(#wave1)"
      />
      {/* Front wave */}
      <path
        d="M0,0 L0,120 C200,200 400,240 600,180 C800,120 1000,40 1200,80 C1350,110 1410,160 1440,180 L1440,0 Z"
        fill="url(#wave2)"
      />
    </svg>

    {/* Right soft blob */}
    <div style={{
      position: 'absolute', top: '5%', right: '-5%',
      width: '35%', height: '45%',
      borderRadius: '50%',
      background: 'radial-gradient(ellipse, rgba(243,109,36,0.3) 0%, transparent 70%)',
    }} />
  </div>
);

const Login = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true });
  }, [isAuthenticated, navigate]);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/api/auth/google-url`);
      const { oauth_url } = res.data;

      const popup = window.open(oauth_url, 'google-login', 'width=520,height=640');

      const handler = (event) => {
        if (event.data?.type === 'GOOGLE_AUTH_SUCCESS') {
          window.removeEventListener('message', handler);
          login(event.data.token, event.data.user);
          popup?.close();
          navigate('/', { replace: true });
        }
        if (event.data?.type === 'GOOGLE_AUTH_ERROR') {
          window.removeEventListener('message', handler);
          setError(event.data.message);
          setLoading(false);
          popup?.close();
        }
      };
      window.addEventListener('message', handler);

      const pollClose = setInterval(() => {
        if (popup?.closed) {
          clearInterval(pollClose);
          window.removeEventListener('message', handler);
          setLoading(false);
        }
      }, 500);

    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start login');
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      <WaveBackground />

      {/* Login card */}
      <div style={{
        position: 'relative', zIndex: 1,
        background: '#ffffff',
        borderRadius: 16,
        boxShadow: '0 8px 40px rgba(0,0,0,0.12)',
        padding: '3rem 2.5rem',
        width: '100%', maxWidth: 420,
        margin: '1rem',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
      }}>
        {/* Dialog logo */}
        <img
          src="https://dialog.lk/themes/custom/dialog_theme/logo.svg"
          alt="Dialog"
          style={{ height: 48, marginBottom: '1.75rem' }}
          onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex'; }}
        />
        {/* Fallback logo if SVG fails to load */}
        <div style={{ display: 'none', marginBottom: '1.75rem' }}>
          <DialogLogo size={160} />
        </div>

        <p style={{ color: '#6c757d', fontSize: '0.85rem', marginBottom: '2rem', textAlign: 'center' }}>
          Sign in with your Google account to continue
        </p>

        {/* Google sign-in button */}
        <button
          onClick={handleGoogleLogin}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 12, width: '100%',
            padding: '0.85rem 1.5rem',
            borderRadius: 50,
            border: '1.5px solid #E5E7EB',
            background: loading ? '#F9FAFB' : '#ffffff',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 600, fontSize: '0.95rem', color: '#374151',
            boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
            transition: 'all 0.15s',
            outline: 'none',
          }}
          onMouseEnter={e => { if (!loading) { e.currentTarget.style.boxShadow = '0 3px 12px rgba(0,0,0,0.15)'; e.currentTarget.style.borderColor = '#D1D5DB'; }}}
          onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 1px 6px rgba(0,0,0,0.08)'; e.currentTarget.style.borderColor = '#E5E7EB'; }}
        >
          {loading ? (
            <Loader className="w-5 h-5 animate-spin" style={{ color: '#ff4e2e' }} />
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
          )}
          {loading ? 'Opening Google sign-in...' : 'Continue with Google'}
        </button>

        {error && (
          <div style={{
            marginTop: '1rem', padding: '0.75rem 1rem',
            background: '#FEF2F2', borderRadius: 8,
            border: '1px solid #FEE2E2',
            color: '#DC2626', fontSize: '0.8rem',
            width: '100%', textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        <p style={{
          marginTop: '2rem', fontSize: '0.72rem',
          color: '#C4C9D4', textAlign: 'center', lineHeight: 1.5,
        }}>
          Internal tool · Dialog Axiata PLC<br />
          By signing in you agree to Dialog's usage policies
        </p>
      </div>
    </div>
  );
};

export default Login;