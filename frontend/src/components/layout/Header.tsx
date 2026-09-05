import React from 'react';
import { Link } from 'react-router-dom';
import { SearchBar } from '../common/SearchBar';
import { useDatabaseMode } from '../../context/DatabaseModeContext';

export const Header: React.FC = () => {
  const { isLive, toggleMode, isSwitching } = useDatabaseMode();

  return (
    <header className="h-16 border-b border-slate-700/50 px-6 flex items-center justify-between shrink-0 select-none z-30 sticky top-0 bg-transparent">
      {/* Left: Quick Search */}
      <div className="flex items-center gap-4 flex-1">
        <div className="w-full max-w-md">
          {/* Note: Ensure SearchBar is also styled for dark mode later */}
          <SearchBar />
        </div>
      </div>

      {/* Right: Webhook Link, Demo/Live Toggle & Compact Profile */}
      <div className="flex items-center gap-4">
        {/* Small Webhook Simulator Access Button */}
        <Link
          to="/webhooks"
          target="_blank"
          rel="noopener noreferrer"
          title="Open standalone Gateway Webhook Simulator in a new tab"
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold text-violet-300 bg-violet-900/30 hover:bg-violet-800/40 border border-violet-500/30 transition-all duration-200 group"
        >
          <span className="text-violet-400 font-bold group-hover:scale-110 transition-transform drop-shadow-[0_0_8px_rgba(139,92,246,0.5)]">⚡</span>
          <span className="tracking-wide">Gateway Simulator</span>
        </Link>

        {/* Demo / Live Mode Switcher */}
        <button
          type="button"
          onClick={toggleMode}
          disabled={isSwitching}
          title={
            isLive
              ? 'Click to switch to Demo Mode'
              : 'Click to switch to Live Mode'
          }
          className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold font-mono transition-all duration-300 cursor-pointer select-none ${
            isLive
              ? 'bg-cyan-900/30 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-800/40 shadow-[0_0_15px_-3px_rgba(6,182,212,0.2)]'
              : 'bg-slate-800/50 text-slate-300 border border-slate-600 hover:bg-slate-700/50'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              isLive ? 'bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(34,211,238,0.8)]' : 'bg-slate-500'
            }`}
          />
          <span className="tracking-widest uppercase">{isLive ? 'LIVE CLUSTER' : 'DEMO NODE'}</span>
        </button>

        {/* Compact Merchant Profile */}
        <div className="flex items-center gap-3 pl-4 border-l border-slate-700/50">
          <div className="flex flex-col min-w-0 max-w-[120px] text-right">
            <span className="font-bold text-slate-200 text-[13px] truncate leading-tight tracking-wide">
              Nexus Electronics
            </span>
            <span className="text-[10px] text-slate-400 font-mono leading-tight truncate uppercase tracking-widest">
              MID_84729
            </span>
          </div>
          <div className="w-9 h-9 rounded-full bg-slate-900 text-cyan-400 flex items-center justify-center font-bold text-sm shadow-[0_0_15px_-3px_rgba(6,182,212,0.3)] ring-1 ring-cyan-500/50 shrink-0 border border-slate-800">
            N
          </div>
        </div>
      </div>
    </header>
  );
};
