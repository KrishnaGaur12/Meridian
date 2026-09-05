import React from 'react';
import { Link } from 'react-router-dom';
import { SearchBar } from '../common/SearchBar';
import { useDatabaseMode } from '../../context/DatabaseModeContext';

export const Header: React.FC = () => {
  const { isLive, toggleMode, isSwitching } = useDatabaseMode();

  return (
    <header className="h-14 bg-white border-b border-slate-200 shadow-2xs px-6 flex items-center justify-between shrink-0 select-none z-30">
      {/* Left: Quick Search */}
      <div className="flex items-center gap-3">
        <SearchBar />
      </div>

      {/* Right: Webhook Link, Demo/Live Toggle & Compact Profile */}
      <div className="flex items-center gap-3">
        {/* Small Webhook Simulator Access Button */}
        <Link
          to="/webhooks"
          target="_blank"
          rel="noopener noreferrer"
          title="Open standalone Razorpay Webhook Simulator in a new tab"
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-indigo-700 bg-indigo-50/80 hover:bg-indigo-100/90 border border-indigo-200 transition-colors shadow-2xs group"
        >
          <span className="text-indigo-600 font-bold">⚡</span>
          <span>Razorpay Webhook</span>
          <svg className="w-3 h-3 text-indigo-500 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
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
          className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer select-none ${
            isLive
              ? 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100 shadow-2xs'
              : 'bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200 shadow-2xs'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              isLive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
            }`}
          />
          <span className="font-bold">{isLive ? 'Live Mode' : 'Demo Mode'}</span>
        </button>

        {/* Compact Merchant Profile */}
        <div className="flex items-center gap-2 pl-2.5 border-l border-slate-200 text-xs">
          <div className="w-7 h-7 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shadow-2xs shrink-0">
            A
          </div>
          <div className="flex flex-col min-w-0 max-w-[120px]">
            <span className="font-bold text-slate-800 text-xs truncate leading-tight">
              Acme Store
            </span>
            <span className="text-[10px] text-slate-400 font-mono leading-tight truncate">
              MID_001
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
