import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useRealtimeRefresh } from '../../hooks/useRealtimeRefresh';
import { useDatabaseMode } from '../../context/DatabaseModeContext';

export const AppLayout: React.FC = () => {
  useRealtimeRefresh();
  const { isSwitching, mode } = useDatabaseMode();

  return (
    <div className="flex h-screen w-full bg-slate-50 overflow-hidden font-sans text-slate-900 selection:bg-indigo-500 selection:text-white antialiased">
      {/* 1. Global Consistent Sidebar */}
      <Sidebar />

      {/* 2. Main Application Viewport */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        <Header />

        {isSwitching && (
          <div className="bg-indigo-600 text-white text-xs py-1.5 px-4 text-center font-medium shadow-xs transition-all flex items-center justify-center gap-2 shrink-0 z-20">
            <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Synchronizing workspace with {mode} database...</span>
          </div>
        )}

        {/* 3. Page Content Area — Fills available width naturally */}
        <main className="flex-1 overflow-y-auto px-6 py-6 w-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
