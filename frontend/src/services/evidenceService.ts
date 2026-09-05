import { api } from './api';
import { appCache } from './cacheService';
import { CreateEvidencePayload, UpdateEvidencePayload, EvidenceItem, ImpactDelta } from '../types/evidence';

export const evidenceService = {
  // 1. Create manual merchant evidence
  async createEvidence(payload: CreateEvidencePayload): Promise<{ evidence: EvidenceItem; impact_delta?: ImpactDelta }> {
    appCache.invalidate(`command_center_${payload.dispute_id}`);
    appCache.invalidate(`package_${payload.dispute_id}`);
    appCache.invalidate(`readiness_${payload.dispute_id}`);
    appCache.invalidate(`analysis_${payload.dispute_id}`);
    const res = await api.post('/evidence', payload);
    return res.data;
  },

  // 2. Upload evidence file (PDF / PNG / JPG)
  async uploadEvidenceFile(
    disputeId: string,
    file: File,
    evidenceType?: string,
    title?: string,
    description?: string
  ): Promise<{ success: boolean; evidence_id: string; verification_status: string; analysis?: any; impact_delta?: ImpactDelta }> {
    appCache.invalidate(`command_center_${disputeId}`);
    appCache.invalidate(`package_${disputeId}`);
    appCache.invalidate(`readiness_${disputeId}`);
    appCache.invalidate(`analysis_${disputeId}`);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('dispute_id', disputeId);
    if (evidenceType) formData.append('evidence_type', evidenceType);
    if (title) formData.append('title', title);
    if (description) formData.append('description', description);

    const res = await api.post('/evidence/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  // 3. Replace backing document for an existing evidence item
  async replaceEvidenceFile(
    evidenceId: string,
    file: File,
    disputeId?: string
  ): Promise<{ success: boolean; evidence_id: string; verification_status: string; analysis?: any; impact_delta?: ImpactDelta }> {
    if (disputeId) {
      appCache.invalidate(`command_center_${disputeId}`);
      appCache.invalidate(`package_${disputeId}`);
      appCache.invalidate(`readiness_${disputeId}`);
      appCache.invalidate(`analysis_${disputeId}`);
    } else {
      appCache.invalidate('command_center');
    }

    const formData = new FormData();
    formData.append('file', file);

    const res = await api.post(`/evidence/${evidenceId}/replace`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  // 4. Update evidence metadata
  async updateEvidence(
    evidenceId: string,
    payload: UpdateEvidencePayload,
    disputeId?: string
  ): Promise<{ evidence_id: string; dispute_id: string; title: string; verification_status: string; impact_delta?: ImpactDelta }> {
    if (disputeId) {
      appCache.invalidate(`command_center_${disputeId}`);
      appCache.invalidate(`package_${disputeId}`);
      appCache.invalidate(`readiness_${disputeId}`);
      appCache.invalidate(`analysis_${disputeId}`);
    } else {
      appCache.invalidate('command_center');
    }
    const res = await api.put(`/evidence/${evidenceId}`, payload);
    return res.data;
  },

  // 5. Approve evidence item explicitly (with backend fallback)
  async approveEvidence(
    disputeId: string,
    evidenceId: string,
    extraData?: Record<string, any>
  ): Promise<any> {
    appCache.invalidate(`command_center_${disputeId}`);
    appCache.invalidate(`package_${disputeId}`);
    appCache.invalidate(`readiness_${disputeId}`);
    appCache.invalidate(`analysis_${disputeId}`);

    try {
      // First try dedicated dispute evidence approve endpoint
      const res = await api.post(`/disputes/${disputeId}/evidence/${evidenceId}/approve`, extraData || {});
      return res.data;
    } catch {
      try {
        // Next try direct evidence approve endpoint
        const res = await api.post(`/evidence/${evidenceId}/approve`, extraData || {});
        return res.data;
      } catch {
        // Fallback: update evidence status with authoritative approval metadata
        const res = await api.put(`/evidence/${evidenceId}`, {
          verification_status: 'APPROVED',
          approval_status: 'APPROVED',
          evidence_data: {
            ...(extraData || {}),
            merchant_approval_status: 'APPROVED',
            merchant_approved: true,
            approved_by: 'MERCHANT',
            approved_at: new Date().toISOString(),
          },
        });
        return res.data;
      }
    }
  },

  // 6. Revoke / Reject evidence item
  async rejectEvidence(
    disputeId: string,
    evidenceId: string,
    reason?: string
  ): Promise<any> {
    appCache.invalidate(`command_center_${disputeId}`);
    appCache.invalidate(`package_${disputeId}`);
    appCache.invalidate(`readiness_${disputeId}`);
    appCache.invalidate(`analysis_${disputeId}`);

    try {
      const res = await api.post(`/disputes/${disputeId}/evidence/${evidenceId}/reject`, { reason });
      return res.data;
    } catch {
      try {
        const res = await api.post(`/evidence/${evidenceId}/reject`, { reason });
        return res.data;
      } catch {
        const res = await api.put(`/evidence/${evidenceId}`, {
          verification_status: 'REJECTED',
          approval_status: 'REJECTED',
          evidence_data: {
            merchant_approval_status: 'REJECTED',
            merchant_approved: false,
            rejection_reason: reason,
          },
        });
        return res.data;
      }
    }
  },

  // 7. Delete evidence item
  async deleteEvidence(evidenceId: string, disputeId?: string): Promise<{ evidence_id: string; deleted: boolean; impact_delta?: ImpactDelta }> {
    if (disputeId) {
      appCache.invalidate(`command_center_${disputeId}`);
      appCache.invalidate(`package_${disputeId}`);
      appCache.invalidate(`readiness_${disputeId}`);
      appCache.invalidate(`analysis_${disputeId}`);
    } else {
      appCache.invalidate('command_center');
    }
    const res = await api.delete(`/evidence/${evidenceId}`);
    return res.data;
  },

  // 8. Generate/evaluate evidence package for dispute
  async generateEvidencePackage(disputeId: string): Promise<any> {
    const res = await api.post(`/disputes/${disputeId}/evidence`);
    return res.data;
  },
};

