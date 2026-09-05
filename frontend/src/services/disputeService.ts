import { api } from './api';
import { appCache } from './cacheService';
import {
  Dispute,
  DisputeTimelineEvent,
  DisputeCaseReadiness,
  DisputeSubmitResponse,
  DisputeOutcomeResponse,
} from '../types/dispute';
import { CommandCenterSnapshot, CaseAnalysis, AIExplainability, NextBestAction, PackageInspection } from '../types/commandCenter';

export const disputeService = {
  // 1. List all disputes (with fast caching & deduplication)
  async getDisputes(caseSource?: string, signal?: AbortSignal, forceRefresh = false): Promise<Dispute[]> {
    const key = `disputes_list_${caseSource || 'all'}`;
    if (forceRefresh) {
      appCache.invalidate(key);
    }
    return appCache.dedupe(
      key,
      async () => {
        const params = caseSource ? { case_source: caseSource } : {};
        const res = await api.get<Dispute[]>('/disputes', { params, signal });
        return res.data;
      },
      15000 // 15 seconds cache
    );
  },

  // 2. Get dispute by ID
  async getDisputeById(disputeId: string, signal?: AbortSignal, forceRefresh = false): Promise<Dispute> {
    const key = `dispute_${disputeId}`;
    if (forceRefresh) {
      appCache.invalidate(key);
    }
    return appCache.dedupe(
      key,
      async () => {
        const res = await api.get<Dispute>(`/disputes/${disputeId}`, { signal });
        return res.data;
      },
      30000
    );
  },

  // 3. Command Center (Authoritative primary single-call aggregator for workspace)
  async getCommandCenter(disputeId: string, signal?: AbortSignal, forceRefresh = false): Promise<CommandCenterSnapshot> {
    const key = `command_center_${disputeId}`;
    if (forceRefresh) {
      appCache.invalidate(key);
    }
    return appCache.dedupe(
      key,
      async () => {
        const res = await api.get<CommandCenterSnapshot>(`/disputes/${disputeId}/command-center`, { signal });
        return res.data;
      },
      30000
    );
  },

  // 4. Case analysis
  async getAnalysis(disputeId: string, signal?: AbortSignal, forceRefresh = false): Promise<CaseAnalysis> {
    const key = `analysis_${disputeId}`;
    if (forceRefresh) {
      appCache.invalidate(key);
    }
    return appCache.dedupe(
      key,
      async () => {
        const res = await api.get<CaseAnalysis>(`/disputes/${disputeId}/analysis`, { signal });
        return res.data;
      },
      30000
    );
  },

  // 5. Explainability
  async getExplainability(disputeId: string, signal?: AbortSignal): Promise<AIExplainability> {
    const res = await api.get<AIExplainability>(`/disputes/${disputeId}/explainability`, { signal });
    return res.data;
  },

  // 6. Next best action
  async getNextAction(disputeId: string, signal?: AbortSignal): Promise<NextBestAction> {
    const res = await api.get<NextBestAction>(`/disputes/${disputeId}/next-action`, { signal });
    return res.data;
  },

  // 7. Case readiness
  async getReadiness(disputeId: string, signal?: AbortSignal, forceRefresh = false): Promise<DisputeCaseReadiness> {
    const key = `readiness_${disputeId}`;
    if (forceRefresh) {
      appCache.invalidate(key);
    }
    return appCache.dedupe(
      key,
      async () => {
        const res = await api.get<DisputeCaseReadiness>(`/disputes/${disputeId}/readiness`, { signal });
        return res.data;
      },
      15000
    );
  },

  // 8. Package inspection
  async getPackageInspection(disputeId: string, signal?: AbortSignal, forceRefresh = false): Promise<PackageInspection> {
    const key = `package_${disputeId}`;
    if (forceRefresh) {
      appCache.invalidate(key);
    }
    return appCache.dedupe(
      key,
      async () => {
        const res = await api.get<PackageInspection>(`/disputes/${disputeId}/package-inspection`, { signal });
        return res.data;
      },
      20000
    );
  },

  // 9. Chronological audit stream
  async getAuditLog(disputeId: string, signal?: AbortSignal): Promise<DisputeTimelineEvent[]> {
    const res = await api.get<DisputeTimelineEvent[]>(`/disputes/${disputeId}/audit`, { signal });
    return res.data;
  },

  // 10. Update merchant defense / rebuttal response statement
  async updateRebuttalResponse(disputeId: string, rebuttalText: string): Promise<any> {
    appCache.invalidate(`command_center_${disputeId}`);
    appCache.invalidate(`package_${disputeId}`);
    try {
      const res = await api.patch(`/disputes/${disputeId}/rebuttal`, { rebuttal_text: rebuttalText });
      return res.data;
    } catch {
      try {
        const res = await api.put(`/disputes/${disputeId}/response`, { rebuttal_text: rebuttalText });
        return res.data;
      } catch {
        const res = await api.patch(`/disputes/${disputeId}`, { rebuttal: { rebuttal_text: rebuttalText } });
        return res.data;
      }
    }
  },

  // 11. Submit dispute package (Hard submission gate)
  async submitDispute(disputeId: string): Promise<DisputeSubmitResponse> {
    appCache.invalidate('disputes_list');
    appCache.invalidate(`dispute_${disputeId}`);
    appCache.invalidate(`command_center_${disputeId}`);
    appCache.invalidate(`readiness_${disputeId}`);
    appCache.invalidate(`package_${disputeId}`);
    const res = await api.post<DisputeSubmitResponse>(`/disputes/${disputeId}/submit`);
    return res.data;
  },

  // 12. Simulate dispute outcome (Simulated WON/LOST resolution)
  async simulateOutcome(disputeId: string): Promise<DisputeOutcomeResponse> {
    appCache.invalidate('disputes_list');
    appCache.invalidate(`dispute_${disputeId}`);
    appCache.invalidate(`command_center_${disputeId}`);
    const res = await api.post<DisputeOutcomeResponse>(`/disputes/${disputeId}/simulate-outcome`);
    return res.data;
  },

  // 13. Accept dispute (Merchant concedes)
  async acceptDispute(disputeId: string, reason: string = 'Merchant accepted dispute'): Promise<any> {
    appCache.invalidate('disputes_list');
    appCache.invalidate(`dispute_${disputeId}`);
    appCache.invalidate(`command_center_${disputeId}`);
    const res = await api.post(`/disputes/${disputeId}/accept`, { reason });
    return res.data;
  },

  // 14. Override AI recommendation
  async overrideRecommendation(
    disputeId: string,
    overrideDecision: 'CONTEST' | 'ACCEPT' | 'INVESTIGATE',
    reason: string
  ): Promise<any> {
    appCache.invalidate(`command_center_${disputeId}`);
    appCache.invalidate(`analysis_${disputeId}`);
    const res = await api.post(`/disputes/${disputeId}/override-recommendation`, {
      override_decision: overrideDecision,
      reason,
    });
    return res.data;
  },

  // 15. Reassess dispute
  async reassessDispute(disputeId: string): Promise<any> {
    appCache.invalidate(`command_center_${disputeId}`);
    appCache.invalidate(`analysis_${disputeId}`);
    appCache.invalidate(`readiness_${disputeId}`);
    appCache.invalidate(`package_${disputeId}`);
    const res = await api.post(`/disputes/${disputeId}/reassess`);
    return res.data;
  },
};

