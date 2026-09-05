import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { simulationService, SimulateDisputeResponse } from '../services/simulationService';
import { SimulationTransaction } from '../types/simulation';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { Skeleton } from '../components/common/Skeleton';
import { formatCurrency, formatDate } from '../utils/formatters';
import { useDatabaseMode } from '../context/DatabaseModeContext';

export const SimulatorPage: React.FC = () => {
  const { isLive, isDemo, setMode, modeVersion } = useDatabaseMode();
  const [transactions, setTransactions] = useState<SimulationTransaction[]>([]);
  const [selectedTxn, setSelectedTxn] = useState<SimulationTransaction | null>(null);
  const [isLoadingTxns, setIsLoadingTxns] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal Dialog States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reasonCode, setReasonCode] = useState<string>('product_not_received');
  const [customReasonDescription, setCustomReasonDescription] = useState<string>('');
  const [disputeDescription, setDisputeDescription] = useState<string>(
    'Customer claims physical goods were never delivered by courier service.'
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Success Confirmation State
  const [createdDispute, setCreatedDispute] = useState<SimulateDisputeResponse | null>(null);

  const navigate = useNavigate();

  // Load available transactions from currently active database
  const loadTransactions = async () => {
    try {
      setIsLoadingTxns(true);
      setError(null);
      const list = await simulationService.getAvailableTransactions();

      // Only show transactions that don't already have an active simulated dispute
      const eligible = list.filter((t) => {
        const status = (t.transaction_status || '').toUpperCase();
        const hasDispute = Boolean(t.has_active_simulated_dispute);
        return (status === 'SUCCESS' || status === 'CAPTURED') && !hasDispute;
      });

      const available = eligible.length > 0 ? eligible : list;
      setTransactions(available);

      // Auto-select first transaction if none selected or selected is no longer in list
      if (available.length > 0) {
        setSelectedTxn(available[0]);
      } else {
        setSelectedTxn(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch transactions.');
    } finally {
      setIsLoadingTxns(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [modeVersion]);

  const handleReasonChange = (reason: string) => {
    setReasonCode(reason);
    if (reason === 'product_not_received') {
      setDisputeDescription('Customer claims physical goods were never delivered by courier service.');
    } else if (reason === 'fraudulent_transaction') {
      setDisputeDescription('Cardholder reports unrecognized charge; card was in their physical possession.');
    } else if (reason === 'duplicate_charge') {
      setDisputeDescription('Customer account was billed twice for the same transaction order.');
    } else if (reason === 'credit_not_processed') {
      setDisputeDescription('Merchant promised a return refund 14 days ago but funds have not credited.');
    } else if (reason === 'product_unacceptable') {
      setDisputeDescription('Received goods are severely damaged, defective, or not as described.');
    } else if (reason === 'other') {
      setDisputeDescription('');
    }
  };

  const handleOpenModal = () => {
    if (!selectedTxn) return;
    setReasonCode('product_not_received');
    setDisputeDescription('Customer claims physical goods were never delivered by courier service.');
    setCustomReasonDescription('');
    setModalError(null);
    setIsModalOpen(true);
  };

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTxn) return;

    if (reasonCode === 'other' && !customReasonDescription.trim()) {
      setModalError('Description is required when selecting "Other" dispute reason.');
      return;
    }

    try {
      setIsSubmitting(true);
      setModalError(null);

      const description =
        reasonCode === 'other'
          ? customReasonDescription.trim()
          : disputeDescription.trim();

      const payload = {
        transaction_id: selectedTxn.transaction_id,
        reason_code: reasonCode,
        reason_description: description,
        phase: 'chargeback',
      };

      const result = await simulationService.simulateDispute(payload);

      // Close modal & set created dispute
      setIsModalOpen(false);
      setCreatedDispute(result);

      // Refresh transactions list
      loadTransactions();
    } catch (err: any) {
      setModalError(err.message || 'Failed to raise dispute against transaction.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full space-y-4 pb-6 flex-1 flex flex-col">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-1 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              Razorpay Payment & Dispute Simulator
            </h1>
            <span
              className={`px-2.5 py-0.5 text-[10px] font-bold rounded-full border ${
                isLive
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                  : 'bg-slate-100 text-slate-600 border-slate-300'
              }`}
            >
              {isLive ? 'LIVE MODE' : 'DEMO MODE'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Select a live transaction to simulate an inbound card network chargeback and trigger autonomous AI triage.
          </p>
        </div>
      </div>

      {/* Demo Mode Notice */}
      {isDemo && (
        <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
            <span>
              <strong>Demo Mode (Read-Only):</strong> Switch to <strong>Live Mode</strong> to simulate live chargebacks and create interactive dispute records.
            </span>
          </div>
          <Button
            onClick={() => setMode('LIVE')}
            variant="primary"
            size="sm"
            className="bg-amber-600 hover:bg-amber-700 text-white shrink-0 font-semibold"
          >
            Switch to Live Mode &rarr;
          </Button>
        </div>
      )}

      {/* Success Banner Card */}
      {createdDispute && (
        <Card className="p-5 bg-emerald-50/70 border-emerald-300 space-y-3 shadow-2xs animate-in fade-in duration-200">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm shrink-0">
                ✓
              </div>
              <div>
                <h3 className="text-sm font-bold text-emerald-950">Dispute Created Successfully</h3>
                <p className="text-xs text-emerald-800">
                  Case <strong className="font-mono text-emerald-950 font-bold">{createdDispute.dispute_id}</strong> is registered and triaged by AI.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setCreatedDispute(null)}
              className="text-emerald-700 hover:text-emerald-900 p-1 text-xs font-bold cursor-pointer"
            >
              ✕
            </button>
          </div>

          <div className="p-3 bg-white rounded-lg border border-emerald-200 text-xs grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-700">
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Dispute ID:</span>
              <strong className="font-mono text-slate-900">{createdDispute.dispute_id}</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Transaction ID:</span>
              <strong className="font-mono text-slate-900">{createdDispute.transaction_id}</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Disputed Value:</span>
              <strong className="text-slate-900">{formatCurrency(createdDispute.amount, createdDispute.currency)}</strong>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block font-mono">Initial AI Action:</span>
              <span className="text-indigo-700 font-bold">
                {createdDispute.case_analysis_summary?.recommendation || 'CONTEST'}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-1">
            <Button
              onClick={() => setCreatedDispute(null)}
              variant="outline"
              size="sm"
              className="bg-white border-emerald-300 text-emerald-900 text-xs"
            >
              Dismiss
            </Button>
            <Button
              onClick={() => navigate(`/disputes/${createdDispute.dispute_id}`)}
              variant="primary"
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 font-semibold text-xs shadow-2xs"
            >
              View Dispute &rarr;
            </Button>
          </div>
        </Card>
      )}

      {/* Main Simulator Content: Two Column Layout (Transaction List on Left, Context & Raise Action on Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1 items-start">
        {/* Left Column: Available Transactions List (7 cols) */}
        <div className="lg:col-span-7 space-y-2.5">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
              Available Transactions ({transactions.length})
            </h2>
            <span className="text-[11px] text-slate-400">Click a card to select</span>
          </div>

          {isLoadingTxns ? (
            <div className="space-y-2.5">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : error ? (
            <Card className="p-6 text-center text-rose-600 text-xs border-rose-200">
              {error}
            </Card>
          ) : transactions.length === 0 ? (
            <Card className="p-8 text-center text-xs text-slate-500 bg-white border-slate-200">
              No eligible transactions available.
            </Card>
          ) : (
            <div className="space-y-2 max-h-[calc(100vh-230px)] overflow-y-auto pr-1">
              {transactions.map((t) => {
                const isSelected = selectedTxn?.transaction_id === t.transaction_id;

                return (
                  <div
                    key={t.transaction_id}
                    onClick={() => setSelectedTxn(t)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer select-none bg-white ${
                      isSelected
                        ? 'border-indigo-600 ring-2 ring-indigo-500/20 shadow-xs'
                        : 'border-slate-200 hover:border-slate-300 hover:shadow-2xs'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      {/* Radio Indicator & Transaction ID */}
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div
                          className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 ${
                            isSelected
                              ? 'border-indigo-600 bg-indigo-600'
                              : 'border-slate-300 bg-white'
                          }`}
                        >
                          {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                        </div>
                        <div className="min-w-0">
                          <span className="font-mono font-bold text-xs text-slate-900 truncate block">
                            {t.transaction_id}
                          </span>
                          <span className="text-[11px] text-slate-500 truncate block">
                            Customer: {t.customer_id}
                          </span>
                        </div>
                      </div>

                      {/* Amount & Status */}
                      <div className="text-right shrink-0">
                        <div className="font-bold text-xs text-slate-900">
                          {formatCurrency(t.amount, t.currency)}
                        </div>
                        <div className="flex items-center justify-end gap-1.5 mt-0.5">
                          <span className="text-[10px] font-mono text-slate-500 uppercase">
                            {t.payment_method}
                          </span>
                          <span className="px-1.5 py-0.2 text-[9px] font-bold rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                            {t.transaction_status || 'Captured'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span>Country: {t.transaction_country || 'IN'}</span>
                      <span>{formatDate(t.timestamp)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Transaction Context & Action Button (5 cols) */}
        <div className="lg:col-span-5 space-y-3 sticky top-0">
          <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
            Transaction Details
          </h2>

          {selectedTxn ? (
            <Card className="p-4 space-y-4 bg-white border-slate-200 shadow-2xs">
              <div>
                <span className="text-[10px] font-mono text-indigo-600 font-bold uppercase tracking-wider">
                  Selected Target
                </span>
                <h3 className="font-mono font-bold text-sm text-slate-900 mt-0.5">
                  {selectedTxn.transaction_id}
                </h3>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500">Amount</span>
                  <strong className="text-slate-900 font-semibold">
                    {formatCurrency(selectedTxn.amount, selectedTxn.currency)}
                  </strong>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500">Customer ID</span>
                  <span className="text-slate-800 font-mono">{selectedTxn.customer_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500">Payment Method</span>
                  <span className="text-slate-800 uppercase font-mono font-medium">{selectedTxn.payment_method}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-200/60">
                  <span className="text-slate-500">Transaction Status</span>
                  <span className="text-emerald-700 font-semibold">{selectedTxn.transaction_status || 'CAPTURED'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Date</span>
                  <span className="text-slate-700 font-mono text-[11px]">{formatDate(selectedTxn.timestamp)}</span>
                </div>
              </div>

              {/* Action: Open Raise Dispute Dialog */}
              <div className="pt-2">
                <Button
                  onClick={handleOpenModal}
                  variant="primary"
                  size="md"
                  className="w-full bg-rose-600 hover:bg-rose-700 font-bold text-xs shadow-xs py-2.5"
                >
                  Raise Dispute &rarr;
                </Button>
                <p className="text-[10px] text-slate-400 text-center mt-2">
                  Opens configuration dialog to select reason code and customer claim details.
                </p>
              </div>
            </Card>
          ) : (
            <Card className="p-6 text-center text-xs text-slate-500 bg-white border-slate-200">
              Select a transaction from the list on the left to review its details and raise a dispute.
            </Card>
          )}
        </div>
      </div>

      {/* POPUP DIALOG: Raise Dispute Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Raise a Dispute"
        subtitle="Simulate an incoming cardholder chargeback inquiry against this transaction."
        footer={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              onClick={handleModalSubmit}
              className="bg-rose-600 hover:bg-rose-700 font-bold shadow-xs"
            >
              Raise Dispute
            </Button>
          </>
        }
      >
        <form onSubmit={handleModalSubmit} className="space-y-4 text-xs">
          {modalError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs">
              {modalError}
            </div>
          )}

          {/* Transaction Summary Card inside Modal */}
          {selectedTxn && (
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-700 flex items-center justify-between">
              <div>
                <span className="text-[10px] text-slate-400 block font-mono">Target Transaction:</span>
                <span className="font-mono font-bold text-slate-900">{selectedTxn.transaction_id}</span>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 block font-mono">Dispute Value:</span>
                <span className="font-bold text-slate-900">{formatCurrency(selectedTxn.amount, selectedTxn.currency)}</span>
              </div>
            </div>
          )}

          {/* Dispute Reason Selection (Radio Options) */}
          <div className="space-y-2">
            <label className="block font-bold text-slate-900 text-xs">
              Dispute Reason *
            </label>
            <div className="space-y-1.5">
              {[
                { id: 'product_not_received', label: 'Product Not Received (10.4)' },
                { id: 'fraudulent_transaction', label: 'Fraudulent Transaction / Unauthorized (10.1)' },
                { id: 'duplicate_charge', label: 'Duplicate Charge (10.2)' },
                { id: 'product_unacceptable', label: 'Product Unacceptable / Defective (10.5)' },
                { id: 'credit_not_processed', label: 'Credit Not Processed (10.3)' },
                { id: 'other', label: 'Other (Custom Reason)' },
              ].map((r) => {
                const isChecked = reasonCode === r.id;
                return (
                  <label
                    key={r.id}
                    onClick={() => handleReasonChange(r.id)}
                    className={`flex items-center gap-2.5 p-2.5 rounded-lg border cursor-pointer transition select-none ${
                      isChecked
                        ? 'border-indigo-600 bg-indigo-50/50 text-indigo-950 font-semibold'
                        : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name="dispute_reason"
                      checked={isChecked}
                      onChange={() => handleReasonChange(r.id)}
                      className="text-indigo-600 focus:ring-indigo-500 h-3.5 w-3.5"
                    />
                    <span>{r.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* If "Other" is selected, require custom description */}
          {reasonCode === 'other' ? (
            <div className="space-y-1.5 p-3 bg-amber-50/60 rounded-xl border border-amber-200">
              <label className="block font-bold text-amber-950 text-xs">
                Reason Description * (Required for 'Other')
              </label>
              <textarea
                rows={2}
                required
                placeholder="Describe the custom chargeback reason..."
                value={customReasonDescription}
                onChange={(e) => setCustomReasonDescription(e.target.value)}
                className="w-full bg-white border border-amber-300 rounded-lg p-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-500/30 text-xs"
              />
              <p className="text-[10px] text-amber-800">
                AI Autopilot will analyze this description to automatically construct tailored evidence requirements.
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              <label className="block font-medium text-slate-700 text-xs">
                Customer / Bank Claim Narrative
              </label>
              <textarea
                rows={2}
                value={disputeDescription}
                onChange={(e) => setDisputeDescription(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-900 text-xs leading-relaxed"
              />
            </div>
          )}
        </form>
      </Modal>
    </div>
  );
};
