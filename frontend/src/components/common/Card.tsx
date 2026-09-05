import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className, hoverEffect = false, ...props }) => {
  return (
    <div
      className={twMerge(
        clsx(
          'bg-white rounded-xl border border-slate-200/90 shadow-xs p-6 transition-all duration-150',
          hoverEffect && 'hover:border-slate-300 hover:shadow-sm',
          className
        )
      )}
      {...props}
    >
      {children}
    </div>
  );
};
