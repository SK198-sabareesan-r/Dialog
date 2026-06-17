import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Upload, Search, Activity,
  Menu, X, LogOut, ChevronRight,
} from 'lucide-react';

/* ── Dialog logo — matches screenshot: circle avatar + "Dialog / Support Portal" ── */
const DialogLogoBlock = () => (
  <div className="flex items-center gap-3 px-5 py-5 border-b" style={{ borderColor: '#E8EAF0' }}>
    {/* Circle logo */}
    <div
      style={{
        width: 40, height: 40, borderRadius: '50%',
        background: 'linear-gradient(135deg, #E91E8C 0%, #C91578 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        boxShadow: '0 2px 8px rgba(233,30,140,0.35)',
      }}
    >
      <span style={{ color: '#FFFFFF', fontWeight: 900, fontSize: 18, lineHeight: 1, letterSpacing: '-1px' }}>
        D
      </span>
    </div>
    <div>
      <p style={{ fontWeight: 700, fontSize: '1rem', color: '#1A1A2E', lineHeight: 1.2 }}>Dialog</p>
      <p style={{ fontSize: '0.72rem', color: '#9CA3AF', marginTop: 2 }}>BDA Pipeline</p>
    </div>
  </div>
);

/* ── User badge at top-right (matches screenshot) ── */
const UserBadge = () => (
  <div
    className="hidden md:flex items-center gap-2 px-5 py-3 border-b"
    style={{ borderColor: '#E8EAF0' }}
  >
    <div
      style={{
        width: 30, height: 30, borderRadius: '50%',
        background: '#F3F4F6',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: '1px solid #E8EAF0',
        flexShrink: 0,
      }}
    >
      <span style={{ fontSize: 12, fontWeight: 700, color: '#6B7280' }}>M</span>
    </div>
    <div className="flex-1">
      <p style={{ fontSize: '0.8rem', fontWeight: 600, color: '#1A1A2E' }}>manager1</p>
      <p style={{ fontSize: '0.68rem', color: '#9CA3AF' }}>Manager</p>
    </div>
  </div>
);

const navItems = [
  { name: 'Dashboard',  path: '/',           icon: LayoutDashboard },
  { name: 'Upload',     path: '/upload',      icon: Upload          },
  { name: 'Retrieve',   path: '/retrieve',    icon: Search          },
  { name: 'Monitoring', path: '/monitoring',  icon: Activity        },
];

const Sidebar = () => {
  const location  = useLocation();
  const [open, setOpen] = useState(false);

  const NavLink = ({ item, onClick }) => {
    const active = location.pathname === item.path;
    const Icon   = item.icon;
    return (
      <Link
        to={item.path}
        onClick={onClick}
        className="flex items-center gap-3 mx-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group"
        style={{
          background: active ? '#E91E8C' : 'transparent',
          color:      active ? '#FFFFFF' : '#6B7280',
        }}
        onMouseEnter={e => {
          if (!active) {
            e.currentTarget.style.background = '#FDF0F7';
            e.currentTarget.style.color      = '#E91E8C';
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
          <div
            style={{
              width: 32, height: 32, borderRadius: '50%',
              background: '#E91E8C',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <span style={{ color: '#FFF', fontWeight: 900, fontSize: 15 }}>D</span>
          </div>
          <span style={{ fontWeight: 700, color: '#1A1A2E' }}>Dialog</span>
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
        <UserBadge />

        {/* Nav items */}
        <nav className="flex-1 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map(item => (
            <NavLink key={item.path} item={item} onClick={() => setOpen(false)} />
          ))}
        </nav>

        {/* Logout */}
        <div className="py-4 border-t" style={{ borderColor: '#E8EAF0' }}>
          <button
            className="flex items-center gap-3 mx-3 px-3 py-2.5 rounded-lg w-full text-sm font-medium transition-all"
            style={{ color: '#6B7280' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#FDF0F7'; e.currentTarget.style.color = '#E91E8C'; }}
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
