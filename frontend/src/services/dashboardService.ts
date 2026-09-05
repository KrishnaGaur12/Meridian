import { disputeService } from './disputeService';
import { Dispute } from '../types/dispute';

export interface DashboardAttentionBuckets {
  actionRequired: Dispute[];
  reviewRecommended: Dispute[];
  aiHandling: Dispute[];
  submitted: Dispute[];
  resolved: Dispute[];
}

export interface DashboardStats {
  activeCount: number;
  actionRequiredCount: number;
  reviewRecommendedCount: number;
  needsReviewCount: number;
  aiHandlingCount: number;
  submittedCount: number;
  resolvedCount: number;
  totalAtRiskAmount: number;
  totalRecoveredAmount: number;
  currency: string;
}

export interface DashboardData {
  stats: DashboardStats;
  buckets: DashboardAttentionBuckets;
  needsAttentionDisputes: Dispute[];
  recentDisputes: Dispute[];
  resolvedDisputes: Dispute[];
  allDisputes: Dispute[];
}

export const dashboardService = {
  async getDashboardData(): Promise<DashboardData> {
    const disputes = await disputeService.getDisputes();

    let activeCount = 0;
    let actionRequiredCount = 0;
    let reviewRecommendedCount = 0;
    let aiHandlingCount = 0;
    let submittedCount = 0;
    let resolvedCount = 0;
    let totalAtRiskAmount = 0;
    let totalRecoveredAmount = 0;

    const actionRequired: Dispute[] = [];
    const reviewRecommended: Dispute[] = [];
    const aiHandling: Dispute[] = [];
    const submitted: Dispute[] = [];
    const resolved: Dispute[] = [];
    const needsAttention: Dispute[] = [];

    for (const d of disputes) {
      const status = (d.status || '').toUpperCase();
      const stage = (d.workflow_stage || '').toUpperCase();
      const attention = (d.merchant_attention_state || '').toUpperCase();
      const amt = d.amount || 0;

      if (status === 'WON') {
        resolvedCount++;
        totalRecoveredAmount += amt;
        resolved.push(d);
      } else if (status === 'LOST' || status === 'CLOSED' || stage === 'RESOLVED') {
        resolvedCount++;
        resolved.push(d);
      } else if (stage === 'SUBMITTED' || status === 'UNDER_REVIEW' || attention === 'WAITING') {
        submittedCount++;
        activeCount++;
        totalAtRiskAmount += amt;
        submitted.push(d);
      } else {
        activeCount++;
        totalAtRiskAmount += amt;

        if (attention === 'ACTION_REQUIRED') {
          actionRequiredCount++;
          actionRequired.push(d);
          needsAttention.push(d);
        } else if (attention === 'REVIEW_RECOMMENDED' || stage === 'MERCHANT_REVIEW') {
          reviewRecommendedCount++;
          reviewRecommended.push(d);
          needsAttention.push(d);
        } else if (attention === 'AI_HANDLING' || stage === 'EVIDENCE_COLLECTION' || stage === 'DISPUTE_RAISED') {
          aiHandlingCount++;
          aiHandling.push(d);
        } else {
          reviewRecommendedCount++;
          reviewRecommended.push(d);
          needsAttention.push(d);
        }
      }
    }

    // Sort needsAttention by urgent first, then deadline
    needsAttention.sort((a, b) => {
      const aUrgent = a.merchant_attention_state === 'ACTION_REQUIRED' ? 0 : 1;
      const bUrgent = b.merchant_attention_state === 'ACTION_REQUIRED' ? 0 : 1;
      if (aUrgent !== bUrgent) return aUrgent - bUrgent;
      return (a.remaining_hours ?? 999) - (b.remaining_hours ?? 999);
    });

    return {
      stats: {
        activeCount,
        actionRequiredCount,
        reviewRecommendedCount,
        needsReviewCount: actionRequiredCount + reviewRecommendedCount,
        aiHandlingCount,
        submittedCount,
        resolvedCount,
        totalAtRiskAmount,
        totalRecoveredAmount,
        currency: 'INR',
      },
      buckets: {
        actionRequired,
        reviewRecommended,
        aiHandling,
        submitted,
        resolved,
      },
      needsAttentionDisputes: needsAttention,
      recentDisputes: disputes.slice(0, 5),
      resolvedDisputes: resolved,
      allDisputes: disputes,
    };
  },
};
