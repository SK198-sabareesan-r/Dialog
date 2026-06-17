import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Upload, Search,
  Menu, X, LogOut, ChevronRight,
} from 'lucide-react';

/* ── Dialog logo — official logo from dialog.lk ── */
const DialogLogoBlock = () => (
  <div className="flex items-center gap-3 px-5 py-5 border-b" style={{ borderColor: '#E8EAF0' }}>
    {/* Dialog official logo */}
    <img
      src="https://dialog.lk/themes/custom/dialog_theme/logo.svg"
      alt="Dialog"
      style={{ height: 28 }}
      onError={(e) => {
        // Fallback to circle logo if image fails to load
        e.target.style.display = 'none';
        e.target.nextSibling.style.display = 'flex';
      }}
    />
    {/* Fallback circle logo */}
    <div
      style={{
        display: 'none',
        width: 40,
        height: 40,
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #E4002B 0%, #C20023 100%)',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: '0 2px 8px rgba(228,0,43,0.35)',
      }}
    >
      <span style={{ color: '#FFFFFF', fontWeight: 900, fontSize: 18, lineHeight: 1, letterSpacing: '-1px' }}>
        D
      </span>
    </div>
    <div style={{ marginLeft: 8 }}>
      <p style={{ fontWeight: 700, fontSize: '0.9rem', color: '#1A1A2E', lineHeight: 1.2 }}>BDA Pipeline</p>
      <p style={{ fontSize: '0.7rem', color: '#9CA3AF', marginTop: 2 }}>Knowledge Base</p>
    </div>
  </div>
);

/* ── User badge at top-right (displays authenticated user from JWT) ── */
const UserBadge = ({ user }) => {
  if (!user) return null;

  // Extract initials from name
  const initials = user.name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .substring(0, 2);

  return (
    <div
      className="hidden md:flex items-center gap-2 px-5 py-3 border-b"
      style={{ borderColor: '#E8EAF0' }}
    >
      {user.picture ? (
        <img
          src={user.picture}
          alt={user.name}
          style={{
            width: 30, height: 30, borderRadius: '50%',
            border: '1px solid #E8EAF0',
            flexShrink: 0,
          }}
        />
      ) : (
        <div
          style={{
            width: 30, height: 30, borderRadius: '50%',
            background: '#F3F4F6',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '1px solid #E8EAF0',
            flexShrink: 0,
          }}
        >
          <span style={{ fontSize: 12, fontWeight: 700, color: '#6B7280' }}>{initials}</span>
        </div>
      )}
      <div className="flex-1">
        <p style={{ fontSize: '0.8rem', fontWeight: 600, color: '#1A1A2E' }}>{user.name}</p>
        <p style={{ fontSize: '0.68rem', color: '#9CA3AF' }}>{user.email}</p>
      </div>
    </div>
  );
};

const navItems = [
  { name: 'Upload',   path: '/upload',   icon: Upload  },
  { name: 'Retrieve', path: '/retrieve', icon: Search  },
];

const Sidebar = () => {
  const location  = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const NavLink = ({ item, onClick }) => {
    const active = location.pathname === item.path;
    const Icon   = item.icon;
    return (
      <Link
        to={item.path}
        onClick={onClick}
        className="flex items-center gap-3 mx-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group"
        style={{
          background: active ? '#E4002B' : 'transparent',
          color:      active ? '#FFFFFF' : '#6B7280',
        }}
        onMouseEnter={e => {
          if (!active) {
            e.currentTarget.style.background = '#FFF5F5';
            e.currentTarget.style.color      = '#E4002B';
          }
        }}
        onMouseLeave={e => {
          if (!active) {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color      = '#6B7280';
          }
        }}
      >
        <Icon className="w-4 h-4 flex-shrink-0" />
        <span className="flex-1">{item.name}</span>
        {active && <ChevronRight className="w-3.5 h-3.5 opacity-70" />}
      </Link>
    );
  };

  return (
    <>
      {/* ── Mobile top bar ── */}
      <div
        className="md:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 h-14"
        style={{ background: '#FFFFFF', borderBottom: '1px solid #E8EAF0', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
      >
        <div className="flex items-center gap-2.5">
          <img
            src="https://dialog.lk/themes/custom/dialog_theme/logo.svg"
            alt="Dialog"
            style={{ height: 22 }}
            onError={(e) => {
              // Fallback to circle logo
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'flex';
            }}
          />
          {/* Fallback circle logo */}
          <div
            style={{
              display: 'none',
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: '#E4002B',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ color: '#FFF', fontWeight: 900, fontSize: 15 }}>D</span>
          </div>
        </div>
        <button onClick={() => setOpen(!open)} style={{ color: '#6B7280' }}>
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* ── Mobile overlay ── */}
      {open && (
        <div
          className="md:hidden fixed inset-0 z-40"
          style={{ background: 'rgba(0,0,0,0.3)' }}
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── Sidebar panel ── */}
      <aside
        className={`
          fixed top-0 left-0 h-full z-40 w-64 flex flex-col
          transition-transform duration-300
          ${open ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
        `}
        style={{
          background:  '#FFFFFF',
          boxShadow:   '2px 0 8px rgba(0,0,0,0.06)',
          borderRight: '1px solid #E8EAF0',
        }}
      >
        <DialogLogoBlock />
        <UserBadge user={user} />

        {/* Nav items */}
        <nav className="flex-1 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map(item => (
            <NavLink key={item.path} item={item} onClick={() => setOpen(false)} />
          ))}
        </nav>

        {/* Logout */}
        <div className="py-4 border-t" style={{ borderColor: '#E8EAF0' }}>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 mx-3 px-3 py-2.5 rounded-lg w-full text-sm font-medium transition-all"
            style={{ color: '#6B7280' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#FFF5F5'; e.currentTarget.style.color = '#E4002B'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#6B7280'; }}
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Mobile spacer */}
      <div className="md:hidden h-14" />
    </>
  );
};

export default Sidebar;
