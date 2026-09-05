import React from 'react';
import { Outlet, NavLink, Link } from 'react-router-dom';

export const SimulatorLayout: React.FC = () => {
  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
      isActive
        ? 'bg-slate-900 text-white font-bold shadow-2xs'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
    }`;

  return (
    <div className="w-full space-y-4 flex-1 flex flex-col">
      {/* Simulator Sub-Navigation Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200/80">
        <div className="flex items-center gap-1.5 overflow-x-auto py-0.5">
          <NavLink to="/simulator" end className={navLinkClass}>
            Overview
          </NavLink>
          <NavLink to="/simulator/raise-dispute" className={navLinkClass}>
            + Raise Dispute
          </NavLink>
          <NavLink to="/simulator/transactions" className={navLinkClass}>
            Transactions
          </NavLink>
          <NavLink to="/simulator/disputes" className={navLinkClass}>
            Disputes Registry
          </NavLink>
          <NavLink to="/simulator/customers" className={navLinkClass}>
            Customers
          </NavLink>
          <NavLink to="/simulator/activity" className={navLinkClass}>
            Activity Stream
          </NavLink>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/simulator/raise-dispute"
            className="px-2.5 py-1 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-md transition shadow-2xs"
          >
            + Raise Dispute
          </Link>
        </div>
      </div>

      {/* Simulator Content */}
      <div className="flex-1 flex flex-col">
        <Outlet />
      </div>
    </div>
  );
};
