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
    <div className="flex h-screen w-full bg-[#030712] overflow-hidden font-sans text-slate-300 selection:bg-cyan-500/30 selection:text-cyan-100 antialiased relative">
      
      {/* Dynamic Background Elements */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-900/20 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-violet-900/10 rounded-full blur-[150px] pointer-events-none"></div>

      {/* 1. Floating Dock Sidebar */}
      <div className="z-40 p-4 shrink-0 flex items-center">
        <Sidebar />
      </div>

      {/* 2. Main Application Viewport */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden relative z-10 pt-4 pr-4 pb-4">
        
        {/* Floating Main Canvas Container */}
        <div className="flex-1 flex flex-col bg-slate-900/40 backdrop-blur-3xl border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl relative">
          
          <Header />

          {isSwitching && (
            <div className="bg-cyan-900/80 backdrop-blur-md text-cyan-50 text-xs py-1.5 px-4 text-center font-medium border-b border-cyan-500/30 shadow-lg transition-all flex items-center justify-center gap-2 shrink-0 z-20">
              <svg className="animate-spin h-3.5 w-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="tracking-widest uppercase">Synchronizing neural link with {mode} cluster...</span>
            </div>
          )}

          {/* 3. Page Content Area */}
          <main className="flex-1 overflow-y-auto px-6 py-6 w-full page-enter">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};
