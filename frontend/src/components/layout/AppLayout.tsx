import { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Activity, Bell, Building2, LayoutDashboard, Menu, Moon, Stethoscope, Sun, Truck, WifiOff, X } from 'lucide-react';
import { useLive } from '../../context/live';
import { cn } from '../../lib/utils';
import { SimulationControl } from '../simulation/SimulationControl';
import { Toaster } from '../notifications/Toaster';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/fleet', label: 'Fleet', icon: Truck },
  { to: '/diagnostics', label: 'Diagnostics', icon: Stethoscope },
  { to: '/service', label: 'Service Centers', icon: Building2 },
  { to: '/alerts', label: 'Alerts', icon: Bell },
];

function readTheme(): 'light' | 'dark' {
  try {
    const stored = localStorage.getItem('fixsight-theme');
    if (stored === 'light' || stored === 'dark') return stored;
  } catch {
    /* storage unavailable */
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function AppLayout() {
  const { backendOnline, overview } = useLive();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [theme, setTheme] = useState(readTheme);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    try {
      localStorage.setItem('fixsight-theme', theme);
    } catch {
      /* storage unavailable */
    }
  }, [theme]);

  const attention = (overview?.summary.critical ?? 0) + (overview?.summary.warning ?? 0);

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      {mobileOpen && <div className="fixed inset-0 z-[1040] bg-black/40 lg:hidden" onClick={() => setMobileOpen(false)} />}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-[1050] flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 dark:border-slate-800 dark:bg-slate-900',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center justify-between gap-2 border-b border-slate-200 px-5 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-lg bg-blue-600 text-white">
              <Activity className="size-5" />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight">FixSight</p>
              <p className="text-[11px] leading-tight text-slate-500">Predictive maintenance</p>
            </div>
          </div>
          <button type="button" className="lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close menu">
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white',
                )
              }
            >
              <Icon className="size-4.5" />
              <span className="flex-1">{label}</span>
              {to === '/fleet' && attention > 0 && (
                <span className="rounded-full bg-red-600 px-1.5 text-[11px] font-semibold text-white">{attention}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 p-4 text-xs text-slate-500 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className={cn('size-2 rounded-full', backendOnline ? 'bg-emerald-500' : 'bg-red-500')} />
            {backendOnline ? 'Backend connected' : 'Backend offline'}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-[1030] flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6 dark:border-slate-800 dark:bg-slate-900/90">
          <button type="button" className="rounded-lg p-1.5 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu className="size-5" />
          </button>
          <div className="flex-1" />
          <SimulationControl />
          <button
            type="button"
            onClick={() => setTheme((value) => (value === 'dark' ? 'light' : 'dark'))}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
          </button>
        </header>

        {!backendOnline && (
          <div className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-6 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/60 dark:text-red-300">
            <WifiOff className="size-4" /> Cannot reach the FixSight API. Start the backend (uvicorn app.main:app) or check docker compose.
          </div>
        )}

        <main className="mx-auto w-full max-w-[1600px] flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>

      <Toaster />
    </div>
  );
}
