import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'neutral' | 'urgent' | 'important' | 'success' | 'info' | 'outline';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral', className }) => {
  const base = 'inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded-md border tracking-wide select-none';

  const variants = {
    neutral: 'bg-slate-100 text-slate-700 border-slate-200',
    urgent: 'bg-rose-50 text-rose-700 border-rose-200',
    important: 'bg-amber-50 text-amber-800 border-amber-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    info: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    outline: 'bg-transparent text-slate-600 border-slate-300',
  };

  return <span className={twMerge(clsx(base, variants[variant], className))}>{children}</span>;
};
