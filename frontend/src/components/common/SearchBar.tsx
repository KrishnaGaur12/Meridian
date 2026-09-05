import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { disputeService } from '../../services/disputeService';
import { Dispute } from '../../types/dispute';
import { formatCurrency, formatReasonCode, formatStatus } from '../../utils/formatters';

export const SearchBar: React.FC = () => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [filtered, setFiltered] = useState<Dispute[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    disputeService.getDisputes().then(setDisputes).catch(() => {});
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      setFiltered([]);
      setIsOpen(false);
      return;
    }

    const q = query.toLowerCase().trim();
    const matches = disputes.filter(
      (d) =>
        d.dispute_id.toLowerCase().includes(q) ||
        d.transaction_id.toLowerCase().includes(q) ||
        d.customer_id.toLowerCase().includes(q) ||
        (d.reason_code && d.reason_code.toLowerCase().includes(q)) ||
        (d.reason_description && d.reason_description.toLowerCase().includes(q))
    );
    setFiltered(matches.slice(0, 6));
    setIsOpen(true);
  }, [query, disputes]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (disputeId: string) => {
    setIsOpen(false);
    setQuery('');
    navigate(`/disputes/${disputeId}`);
  };

  return (
    <div className="relative w-full max-w-xs" ref={dropdownRef}>
      <div className="relative flex items-center">
        <span className="absolute left-3 text-slate-400 pointer-events-none">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search dispute, transaction..."
          className="w-full bg-slate-100/80 hover:bg-slate-100 focus:bg-white text-slate-900 placeholder-slate-400 text-xs rounded-lg pl-9 pr-3 py-1.5 border border-transparent focus:border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setIsOpen(false);
            }}
            className="absolute right-2.5 text-slate-400 hover:text-slate-600 p-0.5"
            aria-label="Clear search"
          >
            ✕
          </button>
        )}
      </div>

      {/* Instant Search Results Dropdown */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-white rounded-xl shadow-xl border border-slate-200 z-50 overflow-hidden py-1 max-h-80 overflow-y-auto">
          {filtered.length > 0 ? (
            filtered.map((d) => {
              const statusInfo = formatStatus(d.status, d.workflow_stage, d.merchant_attention_state);
              return (
                <button
                  key={d.dispute_id}
                  onClick={() => handleSelect(d.dispute_id)}
                  className="w-full text-left px-3.5 py-2.5 hover:bg-slate-50 flex items-center justify-between gap-3 border-b border-slate-100 last:border-0 transition"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-xs text-slate-900">{d.dispute_id}</span>
                      <span className="text-[11px] text-slate-500 truncate">{formatReasonCode(d.reason_code)}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      {d.customer_id} · {d.transaction_id}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs font-medium text-slate-900">{formatCurrency(d.amount, d.currency || 'INR')}</div>
                    <div className={`text-[10px] font-medium ${statusInfo.colorClass.split(' ')[0]}`}>{statusInfo.label}</div>
                  </div>
                </button>
              );
            })
          ) : (
            <div className="px-4 py-3 text-xs text-slate-500 text-center">
              No matching disputes found
            </div>
          )}
        </div>
      )}
    </div>
  );
};
