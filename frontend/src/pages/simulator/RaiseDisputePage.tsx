import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { simulationService, SimulateDisputeResponse } from '../../services/simulationService';
import { SimulationTransaction } from '../../types/simulation';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Skeleton } from '../../components/common/Skeleton';
import { formatCurrency } from '../../utils/formatters';
import { useDatabaseMode } from '../../context/DatabaseModeContext';

export const RaiseDisputePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialTxn = searchParams.get('txn') || '';

  const { isLive, isDemo, setMode, modeVersion } = useDatabaseMode();
  const [transactions, setTransactions] = useState<SimulationTransaction[]>([]);
  const [selectedTxnId, setSelectedTxnId] = useState<string>(initialTxn);
  const [selectedTxn, setSelectedTxn] = useState<SimulationTransaction | null>(null);

  const [reasonCode, setReasonCode] = useState<string>('product_not_received');
  const [customReasonDescription, setCustomReasonDescription] = useState<string>('');
  const [customerNarrative, setCustomerNarrative] = useState<string>(
    'Customer claims physical goods were never delivered by courier service.'
  );
  const [phase, setPhase] = useState<string>('chargeback');

  const [isLoadingTxns, setIsLoadingTxns] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdDispute, setCreatedDispute] = useState<SimulateDisputeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  // Load eligible transactions whenever mode changes
  useEffect(() => {
    let isMounted = true;
    const fetchTxns = async () => {
      try {
        setIsLoadingTxns(true);
        setError(null);
        const list = await simulationService.getAvailableTransactions();
        if (!isMounted) return;

        // Filter for eligible transactions (status is success/captured, no active dispute)
        const eligible = list.filter((t) => {
          const status = (t.transaction_status || '').toUpperCase();
          const hasDispute = Boolean(t.has_active_simulated_dispute);
          return (status === 'SUCCESS' || status === 'CAPTURED') && !hasDispute;
        });

        const activeList = eligible.length > 0 ? eligible : list;
        setTransactions(activeList);

        if (initialTxn) {
          const match = activeList.find((t) => t.transaction_id === initialTxn);
          if (match) {
            setSelectedTxnId(match.transaction_id);
            setSelectedTxn(match);
          } else if (activeList.length > 0) {
            setSelectedTxnId(activeList[0].transaction_id);
            setSelectedTxn(activeList[0]);
          }
        } else if (activeList.length > 0) {
          setSelectedTxnId(activeList[0].transaction_id);
          setSelectedTxn(activeList[0]);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to fetch available transactions from active database.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingTxns(false);
        }
      }
    };

    fetchTxns();
    return () => {
      isMounted = false;
    };
  }, [initialTxn, modeVersion]);

  const handleTxnChange = (txnId: string) => {
    setSelectedTxnId(txnId);
    const match = transactions.find((t) => t.transaction_id === txnId);
    if (match) {
      setSelectedTxn(match);
    }
  };

  const handleReasonChange = (reason: string) => {
    setReasonCode(reason);
    if (reason === 'product_not_received') {
      setCustomerNarrative('Customer claims physical goods were never delivered by courier service.');
    } else if (reason === 'fraudulent_transaction') {
      setCustomerNarrative('Cardholder reports unrecognized charge; card was in their physical possession.');
    } else if (reason === 'duplicate_charge') {
      setCustomerNarrative('Customer account was billed twice for the same transaction order.');
    } else if (reason === 'credit_not_processed' || reason === 'refund_not_processed') {
      setCustomerNarrative('Merchant promised a return refund 14 days ago but funds have not credited.');
    } else if (reason === 'product_unacceptable') {
      setCustomerNarrative('Received goods are severely damaged, defective, or not as described.');
    } else if (reason === 'other') {
      setCustomerNarrative('Customer filed a custom inquiry regarding transaction billing discrepancies.');
    }
  };

  const getAIEvidenceExplanation = (reason: string) => {
    switch (reason) {
      case 'product_not_received':
        return 'AI will require Proof of Delivery (courier tracking, carrier name, delivery timestamp, and recipient signature) to validate fulfillment.';
      case 'fraudulent_transaction':
        return 'AI will require 3D-Secure authentication logs, customer IP address match, prior order history, and device fingerprinting records.';
      case 'duplicate_charge':
        return 'AI will require independent order IDs, distinct timestamps, separate tracking numbers, or proof of distinct goods delivered.';
      case 'product_unacceptable':
        return 'AI will require accurate item description, product specification sheets, customer pre-purchase agreement, and return inspection reports.';
      case 'credit_not_processed':
        return 'AI will require Merchant Cancellation Policy, non-refundable terms acceptance, or proof of processed credit note.';
      case 'other':
        return 'For custom reasons, AI will analyze your reason description, cross-reference invoice items, customer communications, and payment authorization tokens to construct the defense checklist.';
      default:
        return 'AI Autopilot will automatically extract transaction evidence from the database and calculate the optimal rebuttal strategy.';
    }
  };

  const handleSubmitDispute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTxnId) {
      setError('Please select a transaction to dispute.');
      return;
    }

    if (reasonCode === 'other' && !customReasonDescription.trim()) {
      setError('A reason description is required when dispute reason is "Other".');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const description =
        reasonCode === 'other'
          ? customReasonDescription.trim()
          : customerNarrative.trim();

      const payload = {
        transaction_id: selectedTxnId,
        reason_code: reasonCode,
        reason_description: description,
        phase: phase,
      };

      const result = await simulationService.simulateDispute(payload);
      setCreatedDispute(result);
    } catch (err: any) {
      setError(err.message || 'Failed to simulate dispute.');
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="pb-1 border-b border-slate-200/60">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Raise a Dispute</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Simulate an incoming bank chargeback against an eligible transaction
        </p>
      </div>

      {/* Demo Mode Notice */}
      {isDemo && (
        <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            <span>
              <strong>Demo Mode (Read-Only):</strong> You can explore existing demo disputes. To raise new simulated disputes and test the full live evidence workflow, switch to <strong>Live Mode</strong>.
            </span>
          </div>
          <Button
            onClick={() => setMode('LIVE')}
            variant="primary"
            size="sm"
            className="bg-amber-600 hover:bg-amber-700 text-white shrink-0"
          >
            Switch to Live Mode &rarr;
          </Button>
        </div>
      )}

      {createdDispute ? (
        <Card className="p-6 text-center space-y-4 bg-white border-emerald-200 max-w-xl mx-auto my-4 shadow-xs">
          <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto text-xl font-bold">
            ✓
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-slate-900">Dispute Successfully Created</h2>
            <p className="text-xs text-slate-600">
              Dispute <strong className="font-mono text-slate-900 font-bold">{createdDispute.dispute_id}</strong> has been registered in the database and processed by AI Autopilot.
            </p>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-left grid grid-cols-2 gap-2 text-slate-700">
            <div>
              <span className="text-slate-400 block text-[10px]">Dispute ID:</span>
              <strong className="font-mono text-slate-900">{createdDispute.dispute_id}</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Transaction ID:</span>
              <strong className="font-mono text-slate-900">{createdDispute.transaction_id}</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Disputed Value:</span>
              <strong className="text-slate-900 font-semibold">{formatCurrency(createdDispute.amount, createdDispute.currency)}</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Workflow Stage:</span>
              <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 rounded">
                {createdDispute.workflow_stage || 'DISPUTE_RAISED'}
              </span>
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row justify-center gap-3">
            <Button onClick={() => setCreatedDispute(null)} variant="outline" size="sm">
              + Raise Another Dispute
            </Button>
            <Button
              onClick={() => navigate(`/disputes/${createdDispute.dispute_id}`)}
              variant="primary"
              size="sm"
              className="font-semibold shadow-xs"
            >
              Open Merchant Case Workspace &rarr;
            </Button>
          </div>
        </Card>
      ) : (
        <form onSubmit={handleSubmitDispute} className="space-y-4">
          <Card className="p-5 space-y-4 bg-white border-slate-200">
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg flex items-center justify-between">
                <span>{error}</span>
                <button type="button" onClick={() => setError(null)} className="text-rose-600 font-bold p-1">
                  ✕
                </button>
              </div>
            )}

            {/* STEP 1: Select Eligible Transaction */}
            <div className="space-y-2.5 pb-4 border-b border-slate-100">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Step 1: Select Eligible Transaction
                </h3>
                <span className="text-[11px] text-slate-500 font-mono">
                  {transactions.length} eligible records
                </span>
              </div>

              {isLoadingTxns ? (
                <Skeleton className="h-10 w-full" />
              ) : transactions.length === 0 ? (
                <div className="p-4 bg-slate-50 rounded-lg text-xs text-slate-600 border border-slate-200">
                  No eligible transactions found in the active database.
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Select Successful Transaction (No active dispute)
                  </label>
                  <select
                    value={selectedTxnId}
                    onChange={(e) => handleTxnChange(e.target.value)}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 font-medium"
                  >
                    {transactions.map((t) => (
                      <option key={t.transaction_id} value={t.transaction_id}>
                        {t.transaction_id} · {formatCurrency(t.amount, t.currency)} · Customer: {t.customer_id} ({t.payment_method?.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* STEP 2: Realistic Transaction Context Card */}
              {selectedTxn && (
                <div className="p-3.5 bg-slate-50/80 rounded-xl border border-slate-200 text-xs space-y-2">
                  <div className="text-[11px] font-bold text-slate-600 uppercase tracking-wide">
                    Step 2: Transaction Context
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-600">
                    <div>
                      <span className="text-[10px] text-slate-400 block font-mono">Amount</span>
                      <strong className="text-slate-900 font-semibold">{formatCurrency(selectedTxn.amount, selectedTxn.currency)}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block font-mono">Customer</span>
                      <strong className="text-slate-900 font-semibold">{selectedTxn.customer_id}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block font-mono">Payment Method</span>
                      <strong className="text-slate-900 font-semibold uppercase">{selectedTxn.payment_method}</strong>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block font-mono">Transaction Status</span>
                      <span className="px-1.5 py-0.2 text-[10px] font-semibold text-emerald-700 bg-emerald-50 rounded border border-emerald-200">
                        {selectedTxn.transaction_status || 'SUCCESS'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* STEP 3 & 4: Dispute Reason & Narrative */}
            <div className="space-y-3 pb-4 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Step 3 & 4: Dispute Reason & Customer Claim
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Dispute Reason *</label>
                  <select
                    value={reasonCode}
                    onChange={(e) => handleReasonChange(e.target.value)}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 font-medium"
                  >
                    <option value="product_not_received">Product Not Received (10.4)</option>
                    <option value="fraudulent_transaction">Fraudulent / Unauthorized Transaction (10.1)</option>
                    <option value="duplicate_charge">Duplicate Charge (10.2)</option>
                    <option value="product_unacceptable">Defective / Unacceptable Goods (10.5)</option>
                    <option value="credit_not_processed">Credit / Refund Not Processed (10.3)</option>
                    <option value="other">Other (Custom Reason)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Dispute Phase</label>
                  <select
                    value={phase}
                    onChange={(e) => setPhase(e.target.value)}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 font-medium"
                  >
                    <option value="chargeback">Chargeback (Standard)</option>
                    <option value="retrieval">Retrieval Request</option>
                    <option value="pre_arbitration">Pre-Arbitration</option>
                    <option value="arbitration">Arbitration</option>
                  </select>
                </div>
              </div>

              {/* If "Other" is selected, require custom reason description */}
              {reasonCode === 'other' && (
                <div className="p-3 bg-indigo-50/60 rounded-xl border border-indigo-200/80 space-y-2">
                  <label className="block text-xs font-bold text-indigo-950">
                    Reason Description * (Required for 'Other')
                  </label>
                  <textarea
                    rows={2}
                    required
                    placeholder="Describe the specific dispute reason (e.g., Recurring subscription canceled prior to billing cycle)..."
                    value={customReasonDescription}
                    onChange={(e) => setCustomReasonDescription(e.target.value)}
                    className="w-full text-xs bg-white border border-indigo-200 rounded-lg p-2.5 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 leading-relaxed"
                  />
                </div>
              )}

              {/* AI Expected Evidence Requirements Box */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
                <div className="text-[11px] font-bold text-indigo-700 uppercase tracking-wide flex items-center gap-1.5">
                  <span>✨ AI Evidence Requirements</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {getAIEvidenceExplanation(reasonCode)}
                </p>
              </div>

              {/* Step 4: Optional Customer/Bank Dispute Narrative */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Customer / Bank Dispute Narrative (Optional)
                </label>
                <textarea
                  rows={2}
                  value={customerNarrative}
                  onChange={(e) => setCustomerNarrative(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-900 leading-relaxed"
                />
              </div>
            </div>

            {/* STEP 5: Final Dispute Preview */}
            <div className="space-y-2 pb-2">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Step 5: Dispute Preview
              </h3>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-slate-600">
                <div>
                  <span className="text-[10px] text-slate-400 block font-mono">Dispute Reason</span>
                  <span className="font-semibold text-slate-900 capitalize">
                    {reasonCode.replace(/_/g, ' ')}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block font-mono">Target Amount</span>
                  <span className="font-semibold text-slate-900">
                    {selectedTxn ? formatCurrency(selectedTxn.amount, selectedTxn.currency) : '—'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block font-mono">Simulated Network</span>
                  <span className="font-semibold text-slate-900">Razorpay Banking Gateway</span>
                </div>
              </div>
            </div>

            {/* STEP 6: Raise Dispute Action */}
            <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-100">
              <div className="text-xs text-slate-500">
                Dispatches dispute through the gateway to trigger autonomous AI pipeline assessment.
              </div>

              <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/simulator')}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isSubmitting}
                  className="bg-rose-600 hover:bg-rose-700 font-semibold shadow-xs"
                >
                  Step 6: Raise Dispute &rarr;
                </Button>
              </div>
            </div>
          </Card>
        </form>
      )}
    </div>
  );
};
