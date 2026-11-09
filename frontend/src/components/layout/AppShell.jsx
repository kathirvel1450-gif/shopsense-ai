import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Activity, Bot, ChevronLeft, ChevronRight, Database, LayoutDashboard, Settings, ShieldCheck, ShoppingBag, Sparkles, Wifi, WifiOff } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../../services/api.js';

const nav = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/data-quality', label: 'Data Quality', icon: Database },
  { to: '/customers', label: 'Customer Intelligence', icon: Activity },
  { to: '/support', label: 'Support Intelligence', icon: ShieldCheck },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
];
const titles = { '/': 'Overview', '/data-quality': 'Data Quality', '/customers': 'Customer Intelligence', '/support': 'Support Intelligence', '/assistant': 'AI Assistant', '/settings': 'Settings' };

export default function AppShell() {
  const [connected, setConnected] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  useEffect(() => { let live = true; api.health().then((data) => live && setConnected(data?.status === 'ok')).catch(() => live && setConnected(false)); const timer = setInterval(() => api.health().then((d) => live && setConnected(d?.status === 'ok')).catch(() => live && setConnected(false)), 30000); return () => { live = false; clearInterval(timer); }; }, []);
  const title = titles[location.pathname] || 'ShopSense AI';
  return <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
    <aside className="sidebar">
      <NavLink to="/" className="brand"><span className="brand-mark"><Sparkles size={18} /></span><span className="brand-copy">ShopSense <b>AI</b><small>RETAIL INTELLIGENCE</small></span></NavLink>
      <div className="nav-label">WORKSPACE</div><nav aria-label="Main navigation">{nav.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title={label}><Icon size={17} /><span>{label}</span>{to === '/assistant' && <i className="nav-dot" />}</NavLink>)}</nav>
      <div className="nav-label nav-label-bottom">PREFERENCES</div><NavLink to="/settings" className={({ isActive }) => `nav-item ${location.pathname === '/settings' ? 'active' : ''}`} title="Settings"><Settings size={17} /><span>Settings</span></NavLink>
      <a className="nav-item marketplace-link" href="/marketplace.html" title="Open preserved marketplace demo"><ShoppingBag size={17} /><span>Marketplace demo</span></a>
      <div className="sidebar-bottom"><div className="sidebar-status"><span className={`status-pip ${connected ? 'online' : connected === false ? 'offline' : ''}`} /> <span>{connected ? 'Backend connected' : connected === false ? 'Backend offline' : 'Checking backend'}</span></div><button className="collapse-button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>{collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}</button></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>{title}</strong></div><div className={`connection-pill ${connected ? 'is-online' : connected === false ? 'is-offline' : ''}`}>{connected ? <Wifi size={14} /> : <WifiOff size={14} />}<span>{connected ? 'API connected' : connected === false ? 'API unavailable' : 'Connecting'}</span></div></header><main className="main-content"><Outlet /></main><footer className="app-footer"><span><span className="footer-mark">●</span> ShopSense AI</span><span>Retail intelligence · Privacy-first analytics</span></footer></div>
  </div>;
}
