import React from 'react';
import { Card } from '../../components/common/Card';

export const SimulatorMerchantsPage: React.FC = () => {
  return (
    <div className="w-full space-y-4">
      <div className="pb-1 border-b border-slate-200/60">
        <h1 className="text-xl font-bold text-slate-900">Merchants on Network</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Configured merchant accounts integrated with AI Autopilot Risk Engine
        </p>
      </div>

      <Card className="p-0 overflow-hidden bg-white">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-3.5 py-2.5 font-semibold">Merchant ID</th>
              <th className="px-3.5 py-2.5 font-semibold">Business Name</th>
              <th className="px-3.5 py-2.5 font-semibold">Category</th>
              <th className="px-3.5 py-2.5 font-semibold">AI Autopilot Status</th>
              <th className="px-3.5 py-2.5 font-semibold">Integration</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            <tr className="hover:bg-slate-50/80 transition">
              <td className="px-3.5 py-2.5 font-mono font-bold text-slate-900">MERCHANT_001</td>
              <td className="px-3.5 py-2.5 font-semibold text-slate-800">Acme Store</td>
              <td className="px-3.5 py-2.5 text-slate-600">Retail & E-commerce</td>
              <td className="px-3.5 py-2.5">
                <span className="px-2 py-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 rounded border border-emerald-200">
                  Active (Autopilot V2)
                </span>
              </td>
              <td className="px-3.5 py-2.5 font-mono text-slate-500">Live Gateway Boundary</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  );
};
