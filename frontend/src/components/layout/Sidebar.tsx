import React from 'react';
import { NavLink, Link } from 'react-router-dom';

interface NavItemProps {
  to: string;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
  end?: boolean;
}

const NavItem: React.FC<NavItemProps> = ({ to, label, icon, badge, end = false }) => {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center justify-between h-11 px-3.5 rounded-xl text-[13px] font-medium transition-all duration-300 select-none group ${
          isActive
            ? 'bg-cyan-500/10 text-cyan-400 font-semibold border border-cyan-500/20 shadow-[0_0_15px_-3px_rgba(6,182,212,0.15)]'
            : 'text-slate-400 hover:text-cyan-300 hover:bg-slate-800/50 border border-transparent'
        }`
      }
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-5 h-5 flex items-center justify-center shrink-0 transition-transform group-hover:scale-110">
          {icon}
        </div>
        <span className="truncate tracking-wide">{label}</span>
      </div>
      {badge !== undefined && (
        <span className="ml-2 px-1.5 py-0.5 text-[10px] font-bold rounded-md bg-cyan-900/50 text-cyan-300 font-mono shrink-0 border border-cyan-700/50">
          {badge}
        </span>
      )}
    </NavLink>
  );
};

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-[260px] h-[calc(100vh-2rem)] bg-slate-900/40 backdrop-blur-3xl border border-slate-700/50 rounded-2xl flex flex-col shrink-0 select-none shadow-2xl relative overflow-hidden">
      
      {/* Glow effect top left */}
      <div className="absolute top-0 left-0 w-32 h-32 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

      {/* Brand Header */}
      <div className="h-20 px-5 flex items-center relative z-10 border-b border-slate-700/30">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-[#030712] border border-slate-700/80 group-hover:border-cyan-500/50 flex items-center justify-center text-white font-bold text-lg shadow-lg transition-all duration-300 shrink-0 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-violet-500/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <span className="relative z-10 font-display text-cyan-400">M</span>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-slate-100 text-[16px] tracking-widest leading-none uppercase" style={{ fontFamily: 'var(--font-display)' }}>
              Meridian
            </span>
            <span className="text-[10px] text-cyan-500 font-mono tracking-widest leading-tight mt-1 opacity-80">
              SYS.INTELLIGENCE
            </span>
          </div>
        </Link>
      </div>

      {/* Navigation Section */}
      <div className="flex-1 py-5 px-3 space-y-1.5 overflow-y-auto relative z-10">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest font-mono">
          Operations
        </div>

        <NavItem
          to="/"
          end
          label="Overview"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          }
        />

        <NavItem
          to="/disputes"
          label="Disputes"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />

        <NavItem
          to="/history"
          label="History Archive"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />

        <div className="pt-6 px-3 pb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest font-mono">
          System Core
        </div>

        <NavItem
          to="/settings"
          label="Settings & Policies"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          }
        />
      </div>

      {/* Sidebar Footer */}
      <div className="px-5 py-4 border-t border-slate-700/30 relative z-10 bg-slate-900/20">
        <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            <span>SYSTEM ONLINE</span>
          </div>
          <span>v2.0</span>
        </div>
      </div>
    </aside>
  );
};
