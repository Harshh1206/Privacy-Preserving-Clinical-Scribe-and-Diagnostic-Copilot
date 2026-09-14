import { NavLink, useNavigate } from 'react-router-dom';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  exact?: boolean;
}

const IconDashboard = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
    <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
  </svg>
);

const IconPatients = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconRecords = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
    <polyline points="10 9 9 9 8 9"/>
  </svg>
);

const IconShield = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);

const IconLock = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>
);

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: <IconDashboard />, exact: true },
  { to: '/patients', label: 'Patients', icon: <IconPatients /> },
  { to: '/records', label: 'Records', icon: <IconRecords /> },
];

export default function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="w-48 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-screen sticky top-0">
      {/* Logo / App Name */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-brand-600 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <span className="text-sm font-semibold text-slate-100 tracking-tight">ClinicalScribe</span>
        </div>
        <p className="text-2xs text-slate-500 mt-0.5 ml-8">Team C · Physician</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded text-sm transition-colors ${
                isActive
                  ? 'bg-brand-600/15 text-brand-300 font-medium'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              }`
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Privacy indicator */}
      <div className="px-3 py-2 border-t border-slate-800 space-y-1">
        <div className="flex items-center gap-1.5 text-2xs text-ok-400">
          <IconShield />
          <span>End-to-end encrypted</span>
        </div>
        <div className="flex items-center gap-1.5 text-2xs text-slate-500">
          <IconLock />
          <span>HIPAA compliant · SOC 2</span>
        </div>
      </div>

      {/* Physician identity */}
      <div
        className="px-3 py-2.5 border-t border-slate-800 flex items-center gap-2 cursor-pointer hover:bg-slate-800 transition-colors"
        onClick={() => navigate('/')}
      >
        <div className="w-7 h-7 rounded-full bg-brand-700 flex items-center justify-center text-xs font-semibold text-brand-100 shrink-0">
          SC
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium text-slate-200 truncate">Dr. Sarah Chen</p>
          <p className="text-2xs text-slate-500 truncate">Internal Medicine</p>
        </div>
      </div>
    </aside>
  );
}
