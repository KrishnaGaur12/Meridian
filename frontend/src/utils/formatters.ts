export const formatCurrency = (amount: number | null | undefined, currency: string = 'INR'): string => {
  if (amount === null || amount === undefined || isNaN(amount)) return '₹0';
  
  // Format for INR
  if (currency.toUpperCase() === 'INR') {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  }

  // Generic formatting for USD/others
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
    maximumFractionDigits: 2,
  }).format(amount);
};

export const formatReasonCode = (code: string | null | undefined): string => {
  if (!code) return 'Disputed Transaction';
  const reasonMap: Record<string, string> = {
    product_not_received: 'Product Not Received',
    fraudulent_transaction: 'Fraudulent / Unauthorized Transaction',
    duplicate_charge: 'Duplicate Charge',
    refund_not_processed: 'Refund Not Processed',
    product_unacceptable: 'Product Defective or Unacceptable',
    credit_not_processed: 'Credit Not Processed',
    subscription_cancelled: 'Subscription Cancelled',
    general: 'General Inquiry Dispute',
  };

  return reasonMap[code.toLowerCase()] || code.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

export const formatPriority = (
  urgencyLevel?: string,
  remainingHours?: number | null,
  attentionState?: string
): { label: 'URGENT' | 'IMPORTANT' | 'READY' | 'NORMAL'; colorClass: string } => {
  const isUrgent =
    urgencyLevel === 'CRITICAL' ||
    urgencyLevel === 'HIGH' ||
    (remainingHours !== null && remainingHours !== undefined && remainingHours <= 48);

  if (isUrgent || attentionState === 'ACTION_REQUIRED') {
    return {
      label: 'URGENT',
      colorClass: 'text-rose-700 bg-rose-50 border-rose-200 ring-rose-500/20',
    };
  }

  if (attentionState === 'REVIEW_RECOMMENDED') {
    return {
      label: 'IMPORTANT',
      colorClass: 'text-amber-700 bg-amber-50 border-amber-200 ring-amber-500/20',
    };
  }

  if (attentionState === 'AI_HANDLING' || attentionState === 'READY') {
    return {
      label: 'READY',
      colorClass: 'text-emerald-700 bg-emerald-50 border-emerald-200 ring-emerald-500/20',
    };
  }

  return {
    label: 'NORMAL',
    colorClass: 'text-slate-700 bg-slate-100 border-slate-200 ring-slate-400/20',
  };
};

export const formatStatus = (
  status?: string,
  workflowStage?: string,
  attentionState?: string
): { label: string; colorClass: string; isActionable: boolean } => {
  const normalizedStatus = (status || '').toUpperCase();
  const normalizedStage = (workflowStage || '').toUpperCase();

  if (normalizedStatus === 'WON') {
    return {
      label: 'Dispute Won',
      colorClass: 'text-emerald-700 bg-emerald-50 border-emerald-200',
      isActionable: false,
    };
  }

  if (normalizedStatus === 'LOST') {
    return {
      label: 'Dispute Lost',
      colorClass: 'text-rose-700 bg-rose-50 border-rose-200',
      isActionable: false,
    };
  }

  if (normalizedStatus === 'CLOSED') {
    return {
      label: 'Resolved',
      colorClass: 'text-slate-700 bg-slate-100 border-slate-200',
      isActionable: false,
    };
  }

  if (normalizedStage === 'SUBMITTED' || normalizedStatus === 'UNDER_REVIEW' || attentionState === 'WAITING') {
    return {
      label: 'Awaiting Razorpay Review',
      colorClass: 'text-blue-700 bg-blue-50 border-blue-200',
      isActionable: false,
    };
  }

  if (attentionState === 'ACTION_REQUIRED') {
    return {
      label: 'Action Required',
      colorClass: 'text-rose-700 bg-rose-50 border-rose-200',
      isActionable: true,
    };
  }

  if (attentionState === 'REVIEW_RECOMMENDED' || normalizedStage === 'MERCHANT_REVIEW') {
    return {
      label: 'Merchant Review',
      colorClass: 'text-amber-700 bg-amber-50 border-amber-200',
      isActionable: true,
    };
  }

  if (attentionState === 'AI_HANDLING' || normalizedStage === 'EVIDENCE_COLLECTION') {
    return {
      label: 'AI Processing',
      colorClass: 'text-indigo-700 bg-indigo-50 border-indigo-200',
      isActionable: false,
    };
  }

  return {
    label: 'Awaiting Review',
    colorClass: 'text-slate-700 bg-slate-100 border-slate-200',
    isActionable: true,
  };
};

export const formatAIOutcome = (action?: string): { label: string; intent: 'contest' | 'accept' | 'review' } => {
  const normalized = (action || '').toUpperCase();
  if (normalized.includes('ACCEPT') || normalized.includes('CONCEDE')) {
    return { label: 'Accept Dispute', intent: 'accept' };
  }
  if (normalized.includes('INVESTIGATE') || normalized.includes('REVIEW')) {
    return { label: 'Review Further', intent: 'review' };
  }
  return { label: 'Contest Dispute', intent: 'contest' };
};

export const formatAssessment = (
  winProb?: number | null,
  confidence?: string | null
): { label: 'Strong' | 'Moderate' | 'Needs Review' | 'Pending'; badgeClass: string } => {
  if (winProb === undefined || winProb === null) {
    return { label: 'Pending', badgeClass: 'text-slate-700 bg-slate-100 border-slate-200' };
  }
  if (winProb >= 0.75 || (confidence && confidence.toUpperCase() === 'HIGH')) {
    return { label: 'Strong', badgeClass: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
  }
  if (winProb >= 0.45 || (confidence && confidence.toUpperCase() === 'MEDIUM')) {
    return { label: 'Moderate', badgeClass: 'text-amber-700 bg-amber-50 border-amber-200' };
  }
  return { label: 'Needs Review', badgeClass: 'text-rose-700 bg-rose-50 border-rose-200' };
};

export const formatDate = (isoString?: string | null): string => {
  if (!isoString) return 'Pending';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(date);
  } catch {
    return isoString;
  }
};

export const formatDeadlineText = (respondBy?: string | null, remainingHours?: number | null): string => {
  if (!respondBy) return 'No immediate deadline';
  
  if (remainingHours !== null && remainingHours !== undefined) {
    if (remainingHours < 0) return 'Deadline passed';
    if (remainingHours <= 24) return `Due in ${Math.round(remainingHours)} hours`;
    if (remainingHours <= 48) return 'Due tomorrow';
  }

  try {
    const date = new Date(respondBy);
    const dateStr = new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(date);
    return `Response due · ${dateStr}`;
  } catch {
    return `Due: ${respondBy}`;
  }
};
