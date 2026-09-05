import React from 'react';
import { Dispute } from '../../types/dispute';
import { formatCurrency, formatReasonCode, formatPriority, formatStatus, formatDeadlineText } from '../../utils/formatters';

interface CaseHeaderProps {
  dispute: Dispute;
  onRefresh?: () => void;
}

export const CaseHeader: React.FC<CaseHeaderProps> = ({ dispute, onRefresh }) => {
  const priority = formatPriority(dispute.urgency_level, dispute.remaining_hours, dispute.merchant_attention_state);
  const statusInfo = formatStatus(dispute.status, dispute.workflow_stage, dispute.merchant_attention_state);
  const deadlineText = formatDeadlineText(dispute.respond_by, dispute.remaining_hours);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        {/* Dispute Title, Amount & Dual Status/Priority Badges */}
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-lg font-bold text-slate-900">{dispute.dispute_id}</span>
            <span className="text-sm font-semibold text-slate-700">· {formatReasonCode(dispute.reason_code)}</span>
            <span className="text-base font-bold text-slate-900">
              · {formatCurrency(dispute.amount, dispute.currency || 'INR')}
            </span>

            {/* Badges */}
            <div className="flex items-center gap-1.5 ml-auto sm:ml-2">
              <span className={`px-2 py-0.5 text-[11px] font-bold rounded border ${priority.colorClass}`}>
                {priority.label}
              </span>
              <span className={`px-2 py-0.5 text-[11px] font-semibold rounded border ${statusInfo.colorClass}`}>
                {statusInfo.label}
              </span>
            </div>
          </div>

          <p className="text-xs text-slate-500">
            {dispute.reason_description || 'Customer initiated dispute inquiry through issuing bank.'}
          </p>
        </div>

        {/* Refresh button if needed */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 border border-slate-200 hover:bg-slate-50 px-2 py-1 rounded-md transition shrink-0 cursor-pointer"
            title="Re-fetch latest case state"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Sync State
          </button>
        )}
      </div>

      {/* Prominent Deadline & Details Strip */}
      <div className="pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-y-2 gap-x-5 text-xs">
        <div className="flex items-center gap-2 text-rose-700 bg-rose-50/80 border border-rose-200/80 px-2.5 py-1 rounded-md font-medium">
          <svg className="w-3.5 h-3.5 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-semibold">{deadlineText}</span>
        </div>

        <div className="flex flex-wrap items-center gap-3.5 text-slate-600 text-xs">
          <span>Customer: <strong className="text-slate-900 font-semibold">{dispute.customer_id}</strong></span>
          <span>Transaction: <strong className="text-slate-900 font-semibold">{dispute.transaction_id}</strong></span>
          <span>Tier: <span className="font-mono text-[10px] bg-slate-100 px-1.5 py-0.2 rounded text-slate-600 font-medium">{dispute.case_source}</span></span>
        </div>
      </div>
    </div>
  );
};
