import React, { useState, useRef } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { EvidenceItem, ImpactDelta } from '../../types/evidence';
import { evidenceService } from '../../services/evidenceService';
import { formatDate } from '../../utils/formatters';

interface EvidenceSectionProps {
  evidenceList: EvidenceItem[];
  missingEvidence?: string[];
  disputeId: string;
  transactionId: string;
  isReadOnly: boolean;
  onEvidenceChanged: () => void;
  onBack?: () => void;
  onContinue?: () => void;
}

export const EvidenceSection: React.FC<EvidenceSectionProps> = ({
  evidenceList: initialEvidenceList,
  missingEvidence = [],
  disputeId,
  transactionId,
  isReadOnly,
  onEvidenceChanged,
  onBack,
  onContinue,
}) => {
  // Local state with optimistic updates
  const [localEvidence, setLocalEvidence] = useState<EvidenceItem[]>(initialEvidenceList);

  React.useEffect(() => {
    setLocalEvidence(initialEvidenceList);
  }, [initialEvidenceList]);

  // Modal states
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [activeAddTab, setActiveAddTab] = useState<'upload' | 'manual'>('upload');

  // Add form states
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [evidenceType, setEvidenceType] = useState('proof_of_delivery');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [carrier, setCarrier] = useState('FedEx');
  const [trackingNumber, setTrackingNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Edit states
  const [editingItem, setEditingItem] = useState<EvidenceItem | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // Replace file states
  const [replacingItem, setReplacingItem] = useState<EvidenceItem | null>(null);
  const [replaceFile, setReplaceFile] = useState<File | null>(null);
  const [isReplacing, setIsReplacing] = useState(false);
  const replaceInputRef = useRef<HTMLInputElement>(null);

  // Delete confirmation states
  const [deletingItem, setDeletingItem] = useState<EvidenceItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Approving item state
  const [approvingId, setApprovingId] = useState<string | null>(null);

  // Detailed Evidence Intelligence Modal
  const [inspectingItem, setInspectingItem] = useState<EvidenceItem | null>(null);

  // Dynamic Impact Delta Banner & Inline alerts
  const [impactNotice, setImpactNotice] = useState<ImpactDelta | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  React.useEffect(() => {
    if (successMsg) {
      const t = setTimeout(() => setSuccessMsg(null), 5000);
      return () => clearTimeout(t);
    }
  }, [successMsg]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!title) {
        setTitle(file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
      }
    }
  };

  const isItemApproved = (item: EvidenceItem): boolean => {
    const dataObj =
      typeof item.evidence_data === 'object'
        ? item.evidence_data
        : typeof (item as any).data === 'object'
        ? (item as any).data
        : {};

    return (
      item.verification_status === 'APPROVED' ||
      item.approval_status === 'APPROVED' ||
      dataObj?.merchant_approval_status === 'APPROVED' ||
      dataObj?.merchant_approved === true
    );
  };

  const getLifecycleStatus = (item: EvidenceItem) => {
    const raw = (item.ai_analysis_status || item.verification_status || item.status || '').toUpperCase();
    const isApproved = isItemApproved(item);

    if (raw === 'ANALYZING' || raw === 'PROCESSING') {
      return {
        label: 'Analyzing…',
        badgeClass: 'bg-indigo-100 text-indigo-800 border-indigo-300 animate-pulse',
      };
    }
    if (raw === 'FAILED' || raw === 'ERROR' || raw === 'UNAVAILABLE') {
      return {
        label: 'AI Unavailable / Failed',
        badgeClass: 'bg-rose-100 text-rose-800 border-rose-300',
      };
    }
    if (raw === 'REJECTED') {
      return {
        label: 'Rejected',
        badgeClass: 'bg-rose-100 text-rose-800 border-rose-300',
      };
    }
    if (raw === 'NEEDS_REVIEW' || raw === 'FLAGGED') {
      return {
        label: 'Needs Review',
        badgeClass: 'bg-amber-100 text-amber-900 border-amber-300',
      };
    }
    if (raw === 'VERIFIED' || isApproved) {
      return {
        label: isApproved ? 'Verified & Approved' : 'AI Verified',
        badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-300',
      };
    }

    return {
      label: 'Pending Verification',
      badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
    };
  };

  const handleAddEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setErrorMsg('Please provide a document title.');
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);

      if (activeAddTab === 'upload') {
        if (!selectedFile) {
          setErrorMsg('Please select a PDF or image file to upload.');
          setIsSubmitting(false);
          return;
        }

        const tempId = `temp_${Date.now()}`;
        const optimisticItem: EvidenceItem = {
          evidence_id: tempId,
          dispute_id: disputeId,
          title: title.trim(),
          evidence_type: evidenceType,
          description: description.trim() || `Merchant uploaded proof: ${selectedFile.name}`,
          verification_status: 'PENDING_APPROVAL',
          approval_status: 'PENDING_APPROVAL',
          source: 'MERCHANT_FILE_UPLOAD',
          created_at: new Date().toISOString(),
        };
        setLocalEvidence((prev) => [optimisticItem, ...prev]);

        const res = await evidenceService.uploadEvidenceFile(
          disputeId,
          selectedFile,
          evidenceType,
          title.trim(),
          description.trim() || `Merchant uploaded proof: ${selectedFile.name}`
        );

        if (res.impact_delta) {
          setImpactNotice(res.impact_delta);
        }

        setSuccessMsg(`Extracted facts from ${selectedFile.name}. Review and approve before submission.`);
      } else {
        const payload = {
          dispute_id: disputeId,
          transaction_id: transactionId,
          evidence_type: evidenceType,
          title: title.trim(),
          description: description.trim() || 'Manual evidence item provided by merchant.',
          verification_status: 'PENDING_APPROVAL',
          evidence_data: {
            carrier: carrier,
            tracking_number: trackingNumber || `TRK-${Math.floor(100000 + Math.random() * 900000)}`,
            merchant_approval_status: 'PENDING_APPROVAL',
            manual_entry: true,
            created_at: new Date().toISOString(),
          },
        };

        const optimisticItem: EvidenceItem = {
          evidence_id: `temp_${Date.now()}`,
          ...payload,
          source: 'MERCHANT_UPLOAD',
          created_at: new Date().toISOString(),
        };
        setLocalEvidence((prev) => [optimisticItem, ...prev]);

        const res = await evidenceService.createEvidence(payload);
        if (res.impact_delta) {
          setImpactNotice(res.impact_delta);
        }

        setSuccessMsg('Manual proof record saved. Review and approve before submission.');
      }

      setIsAddModalOpen(false);
      resetAddForm();
      onEvidenceChanged();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not process evidence item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleApproval = async (item: EvidenceItem) => {
    if (!item.evidence_id) return;
    const isCurrentlyApproved = isItemApproved(item);

    try {
      setApprovingId(item.evidence_id);
      setErrorMsg(null);

      // Optimistic update
      setLocalEvidence((prev) =>
        prev.map((ev) =>
          ev.evidence_id === item.evidence_id
            ? {
                ...ev,
                verification_status: isCurrentlyApproved ? 'PENDING_APPROVAL' : 'APPROVED',
                approval_status: isCurrentlyApproved ? 'PENDING_APPROVAL' : 'APPROVED',
              }
            : ev
        )
      );

      if (isCurrentlyApproved) {
        await evidenceService.rejectEvidence(item.evidence_id, disputeId);
        setSuccessMsg(`Evidence "${item.title || item.evidence_type}" unapproved.`);
      } else {
        const res = await evidenceService.approveEvidence(disputeId, item.evidence_id);
        if (res?.impact_delta) setImpactNotice(res.impact_delta);
        setSuccessMsg(`Evidence "${item.title || item.evidence_type}" approved for submission.`);
      }

      onEvidenceChanged();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not update approval status.');
    } finally {
      setApprovingId(null);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !editingItem.evidence_id) return;

    try {
      setIsEditing(true);
      setErrorMsg(null);

      const res = await evidenceService.updateEvidence(
        editingItem.evidence_id,
        {
          title: editTitle.trim(),
          description: editDescription.trim(),
          verification_status: 'PENDING_APPROVAL',
          approval_status: 'PENDING_APPROVAL',
        },
        disputeId
      );

      if (res?.impact_delta) setImpactNotice(res.impact_delta);
      setSuccessMsg('Evidence updated — please review and re-approve.');
      setEditingItem(null);
      onEvidenceChanged();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not update evidence.');
    } finally {
      setIsEditing(false);
    }
  };

  const handleReplaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replacingItem || !replacingItem.evidence_id || !replaceFile) {
      setErrorMsg('Please select a replacement file.');
      return;
    }

    try {
      setIsReplacing(true);
      setErrorMsg(null);

      const res = await evidenceService.replaceEvidenceFile(
        replacingItem.evidence_id,
        replaceFile,
        disputeId
      );

      if (res?.impact_delta) setImpactNotice(res.impact_delta);
      setSuccessMsg(`File replaced with ${replaceFile.name}.`);
      setReplacingItem(null);
      setReplaceFile(null);
      onEvidenceChanged();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not replace file.');
    } finally {
      setIsReplacing(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingItem || !deletingItem.evidence_id) return;

    try {
      setIsDeleting(true);
      setErrorMsg(null);

      setLocalEvidence((prev) => prev.filter((ev) => ev.evidence_id !== deletingItem.evidence_id));

      const res = await evidenceService.deleteEvidence(deletingItem.evidence_id, disputeId);
      if (res?.impact_delta) setImpactNotice(res.impact_delta);
      setSuccessMsg('Evidence removed.');
      setDeletingItem(null);
      onEvidenceChanged();
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not delete evidence.');
    } finally {
      setIsDeleting(false);
    }
  };

  const resetAddForm = () => {
    setSelectedFile(null);
    setTitle('');
    setDescription('');
    setTrackingNumber('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const approvedCount = localEvidence.filter(isItemApproved).length;

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      {/* Dynamic Impact Delta Banner */}
      {impactNotice && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-900 shadow-2xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-emerald-700">✓ AI Win Probability Updated:</span>
            <span>
              Changed from {Math.round((impactNotice.win_probability_before || 0) * 100)}% &rarr;{' '}
              <strong className="text-emerald-800 font-bold text-sm">
                {Math.round((impactNotice.win_probability_after || 0) * 100)}%
              </strong>
            </span>
          </div>
          <button
            onClick={() => setImpactNotice(null)}
            className="text-emerald-700 hover:text-emerald-900 text-xs font-bold px-1.5 py-0.5 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Inline Feedback Alerts */}
      {successMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl flex items-center justify-between text-xs animate-in fade-in duration-150">
          <div className="flex items-center gap-2">
            <span className="text-emerald-700 font-bold">✓</span>
            <span className="font-medium">{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg(null)}
            className="text-emerald-700 hover:text-emerald-900 text-xs font-bold px-1.5 py-0.5 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-900 rounded-xl flex items-center justify-between text-xs animate-in fade-in duration-150">
          <div className="flex items-center gap-2">
            <span className="text-rose-700 font-bold">!</span>
            <span className="font-medium">{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-rose-700 hover:text-rose-900 text-xs font-bold px-1.5 py-0.5 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      <Card className="p-5 bg-white border-slate-200 shadow-2xs space-y-4">
        {/* Step Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-mono font-bold text-indigo-700 uppercase tracking-wider">
              Step 3 · Evidence Verification & AI Assessment
            </span>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
              Evidence Package & Fulfillment Proofs
            </h2>
          </div>

          {!isReadOnly && (
            <div className="flex items-center gap-2">
              <Button
                onClick={() => {
                  resetAddForm();
                  setIsAddModalOpen(true);
                }}
                variant="primary"
                size="sm"
                className="bg-indigo-600 hover:bg-indigo-700 font-bold text-xs"
              >
                + Add Evidence
              </Button>
            </div>
          )}
        </div>

        {/* Status Bar */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">Package Status:</span>
            <strong className="text-slate-900">{approvedCount} of {localEvidence.length} Evidence Records Approved</strong>
          </div>
          <span className="text-[11px] font-mono text-slate-500">All attached items must be approved to submit</span>
        </div>

        {/* Evidence Grid */}
        {localEvidence.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-slate-200 rounded-xl p-6">
            <p className="text-sm font-medium text-slate-600">No evidence items attached yet</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Add proof of delivery, tracking numbers, customer communications, or invoice proofs.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {localEvidence.map((item, idx) => {
              const approved = isItemApproved(item);
              const lifecycle = getLifecycleStatus(item);
              const isApprovingThis = approvingId === item.evidence_id;

              return (
                <Card
                  key={item.evidence_id || idx}
                  className={`p-4 space-y-2.5 border bg-white shadow-2xs ${
                    approved
                      ? 'border-emerald-300 ring-1 ring-emerald-100'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 pb-1.5 border-b border-slate-100">
                    <div className="min-w-0 flex-1">
                      <h4 className="text-xs font-bold text-slate-900 truncate">
                        {item.title || item.evidence_type?.replace(/_/g, ' ').toUpperCase()}
                      </h4>
                      <span className="text-[10px] text-slate-400 font-mono block">
                        Type: {item.evidence_type?.replace(/_/g, ' ')}
                      </span>
                    </div>

                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded-md border ${lifecycle.badgeClass}`}>
                        {lifecycle.label}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 line-clamp-2">
                    {item.ai_relevance || item.why_it_matters || item.description || 'Verified fulfillment evidence.'}
                  </p>

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                    <button
                      type="button"
                      onClick={() => setInspectingItem(item)}
                      className="text-[11px] text-indigo-600 hover:text-indigo-800 font-bold underline cursor-pointer"
                    >
                      Inspect AI &rarr;
                    </button>

                    {!isReadOnly && (
                      <div className="flex items-center gap-2">
                        <Button
                          onClick={() => handleToggleApproval(item)}
                          variant={approved ? 'outline' : 'primary'}
                          size="sm"
                          isLoading={isApprovingThis}
                          className={`text-[11px] h-7 px-2.5 ${
                            approved ? 'border-emerald-300 text-emerald-700 hover:bg-emerald-50' : 'bg-emerald-600 hover:bg-emerald-700'
                          }`}
                        >
                          {approved ? '✓ Approved' : 'Approve'}
                        </Button>

                        <button
                          type="button"
                          onClick={() => {
                            setEditingItem(item);
                            setEditTitle(item.title || '');
                            setEditDescription(item.description || '');
                          }}
                          className="text-[11px] text-slate-500 hover:text-slate-800 cursor-pointer"
                        >
                          Edit
                        </button>
                        <span className="text-slate-300">|</span>
                        <button
                          type="button"
                          onClick={() => setDeletingItem(item)}
                          className="text-[11px] text-rose-600 hover:text-rose-800 cursor-pointer"
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Missing Evidence Callout */}
        {missingEvidence.length > 0 && !isReadOnly && (
          <div className="p-3.5 bg-amber-50 rounded-xl border border-amber-200 text-xs space-y-1.5">
            <span className="font-bold text-amber-950 block uppercase font-mono text-[10px]">
              AI Recommended Evidence Gaps ({missingEvidence.length}):
            </span>
            <div className="flex flex-wrap gap-1.5">
              {missingEvidence.map((gap, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-md bg-white border border-amber-300 text-amber-900 font-medium capitalize"
                >
                  {gap.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Step Actions */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack}>
              &larr; Back to Case Overview
            </Button>
          )}
          {onContinue && (
            <Button variant="primary" size="sm" onClick={onContinue} className="ml-auto">
              Continue to Strategy Review &rarr;
            </Button>
          )}
        </div>
      </Card>

      {/* Inspect AI Intelligence Modal */}
      {inspectingItem && (
        <Modal
          isOpen={Boolean(inspectingItem)}
          onClose={() => setInspectingItem(null)}
          title={`AI Verification Breakdown · ${inspectingItem.title || inspectingItem.evidence_type}`}
          subtitle="Machine reasoning and verification dimensions evaluated against the chargeback claim."
        >
          <div className="space-y-4 text-xs text-slate-800">
            <div className="grid grid-cols-2 gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 font-mono text-[11px]">
              <div>
                <span className="text-slate-400 block text-[10px]">Status:</span>
                <strong className="text-emerald-700">{getLifecycleStatus(inspectingItem).label}</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Source:</span>
                <strong className="text-slate-900">{inspectingItem.source || 'DATABASE'}</strong>
              </div>
            </div>

            <div className="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100 space-y-1">
              <span className="font-bold text-indigo-900 uppercase font-mono text-[10px] block">
                AI Assessment & Relevance
              </span>
              <p className="text-slate-800 leading-relaxed font-medium">
                {inspectingItem.ai_relevance || inspectingItem.why_it_matters || inspectingItem.description || 'Verified proof of order fulfillment.'}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-100 flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setInspectingItem(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Add Evidence */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Supporting Evidence"
        subtitle="Upload or record documents supporting fulfillment representation."
      >
        <form onSubmit={handleAddEvidence} className="space-y-4 text-xs">
          <div className="flex border-b border-slate-200">
            <button
              type="button"
              onClick={() => setActiveAddTab('upload')}
              className={`pb-2 px-3 font-semibold cursor-pointer ${
                activeAddTab === 'upload' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-500'
              }`}
            >
              Upload Document
            </button>
            <button
              type="button"
              onClick={() => setActiveAddTab('manual')}
              className={`pb-2 px-3 font-semibold cursor-pointer ${
                activeAddTab === 'manual' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-500'
              }`}
            >
              Structured Entry
            </button>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Evidence Type *</label>
            <select
              value={evidenceType}
              onChange={(e) => setEvidenceType(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
            >
              <option value="proof_of_delivery">Proof of Delivery</option>
              <option value="customer_communication">Customer Communication</option>
              <option value="invoice">Commercial Tax Invoice</option>
              <option value="tos_acceptance">Terms of Service Acceptance</option>
              <option value="refund_policy">Refund Policy</option>
              <option value="ip_address_log">IP Log</option>
            </select>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Title *</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Courier Proof of Delivery"
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
            />
          </div>

          {activeAddTab === 'upload' ? (
            <div>
              <label className="block font-bold text-slate-700 mb-1">File (PDF/Image) *</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileSelect}
                className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-indigo-50 file:text-indigo-700"
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Carrier</label>
                <input
                  type="text"
                  value={carrier}
                  onChange={(e) => setCarrier(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
                />
              </div>
              <div>
                <label className="block font-bold text-slate-700 mb-1">Tracking ID</label>
                <input
                  type="text"
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block font-bold text-slate-700 mb-1">Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
            />
          </div>

          <div className="pt-2 border-t border-slate-100 flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              Save Evidence
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Evidence */}
      <Modal
        isOpen={!!editingItem}
        onClose={() => setEditingItem(null)}
        title="Edit Evidence Record"
        subtitle="Modifying evidence resets its approval status to Pending Approval."
      >
        <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 mb-1">Title *</label>
            <input
              type="text"
              required
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Description</label>
            <textarea
              rows={3}
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900"
            />
          </div>

          <div className="pt-2 border-t border-slate-100 flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setEditingItem(null)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isEditing}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Delete Evidence Confirmation */}
      <Modal
        isOpen={!!deletingItem}
        onClose={() => setDeletingItem(null)}
        title="Delete Evidence Record?"
        subtitle="Removing this evidence may impact case readiness."
      >
        <div className="space-y-3 text-xs text-slate-700">
          <p>
            Are you sure you want to delete <strong>{deletingItem?.title || deletingItem?.evidence_type}</strong>?
          </p>

          <div className="pt-2 border-t border-slate-100 flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setDeletingItem(null)}>
              Cancel
            </Button>
            <Button type="button" variant="danger" size="sm" isLoading={isDeleting} onClick={handleDeleteConfirm}>
              Confirm Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
