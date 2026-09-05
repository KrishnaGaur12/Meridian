import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

export type DatabaseMode = 'DEMO' | 'LIVE';

interface DatabaseModeContextType {
  mode: DatabaseMode;
  isDemo: boolean;
  isLive: boolean;
  setMode: (mode: DatabaseMode) => void;
  toggleMode: () => void;
  isSwitching: boolean;
  modeVersion: number;
}

const DatabaseModeContext = createContext<DatabaseModeContextType | undefined>(undefined);

const STORAGE_KEY = 'razorpay_database_mode';

export const DatabaseModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<DatabaseMode>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === 'LIVE' ? 'LIVE' : 'DEMO';
  });
  const [isSwitching, setIsSwitching] = useState(false);
  const [modeVersion, setModeVersion] = useState(0);

  const applyMode = useCallback((newMode: DatabaseMode) => {
    localStorage.setItem(STORAGE_KEY, newMode);
    api.defaults.headers.common['X-Database-Mode'] = newMode;
    setModeState(newMode);
    setModeVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    // Set initial header on boot
    api.defaults.headers.common['X-Database-Mode'] = mode;
  }, [mode]);

  const setMode = useCallback((newMode: DatabaseMode) => {
    if (newMode === mode) return;
    setIsSwitching(true);
    applyMode(newMode);
    setTimeout(() => {
      setIsSwitching(false);
    }, 300);
  }, [mode, applyMode]);

  const toggleMode = useCallback(() => {
    const nextMode: DatabaseMode = mode === 'DEMO' ? 'LIVE' : 'DEMO';
    setMode(nextMode);
  }, [mode, setMode]);

  return (
    <DatabaseModeContext.Provider
      value={{
        mode,
        isDemo: mode === 'DEMO',
        isLive: mode === 'LIVE',
        setMode,
        toggleMode,
        isSwitching,
        modeVersion,
      }}
    >
      {children}
    </DatabaseModeContext.Provider>
  );
};

export const useDatabaseMode = (): DatabaseModeContextType => {
  const context = useContext(DatabaseModeContext);
  if (!context) {
    throw new Error('useDatabaseMode must be used within a DatabaseModeProvider');
  }
  return context;
};
