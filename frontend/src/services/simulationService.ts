import { api } from './api';
import { SimulateDisputePayload, SimulationTransaction } from '../types/simulation';
import { Dispute } from '../types/dispute';

export interface AvailableTransactionsResponse {
  database?: string;
  total: number;
  total_eligible: number;
  total_transactions: number;
  transactions: SimulationTransaction[];
  all_transactions?: SimulationTransaction[];
}

export interface SimulateDisputeResponse {
  simulation_status?: string;
  dispute_id: string;
  transaction_id: string;
  customer_id: string;
  reason_code: string;
  reason_description: string;
  status: string;
  phase: string;
  case_source?: string;
  merchant_attention_state: string;
  workflow_stage: string;
  respond_by: string;
  amount: number;
  currency: string;
  deadline_info?: any;
  analysis_status?: string;
  analysis_summary?: any;
  case_analysis_summary?: any;
  message?: string;
  dispute?: Dispute;
}

export const simulationService = {
  // 1. Get transactions for webhook dispute simulation (prioritizing /webhooks/transactions for Live DB)
  async getAvailableTransactions(): Promise<SimulationTransaction[]> {
    try {
      const res = await api.get<AvailableTransactionsResponse>('/webhooks/transactions');
      if (res.data && Array.isArray(res.data.transactions)) {
        return res.data.transactions;
      }
    } catch {
      // Fallback to /demo/available-transactions if in DEMO mode or endpoint variance
      const res = await api.get<AvailableTransactionsResponse>('/demo/available-transactions');
      if (res.data && Array.isArray(res.data.transactions)) {
        return res.data.transactions;
      }
      if (Array.isArray(res.data)) {
        return res.data;
      }
    }
    return [];
  },

  async getAllTransactions(): Promise<SimulationTransaction[]> {
    try {
      const res = await api.get<AvailableTransactionsResponse>('/webhooks/transactions');
      if (res.data && Array.isArray(res.data.all_transactions)) {
        return res.data.all_transactions;
      }
      if (res.data && Array.isArray(res.data.transactions)) {
        return res.data.transactions;
      }
    } catch {
      const res = await api.get<AvailableTransactionsResponse>('/demo/available-transactions');
      if (res.data && Array.isArray(res.data.all_transactions)) {
        return res.data.all_transactions;
      }
      if (res.data && Array.isArray(res.data.transactions)) {
        return res.data.transactions;
      }
    }
    return [];
  },

  // 2. Call real Webhook Dispute creation API (Live backend creates dispute in live_database.db and executes AI & ML pipeline)
  async simulateDispute(payload: SimulateDisputePayload): Promise<SimulateDisputeResponse> {
    try {
      const res = await api.post<SimulateDisputeResponse>('/webhooks/razorpay', {
        transaction_id: payload.transaction_id,
        reason_code: payload.reason_code,
        reason_description: payload.reason_description,
        phase: payload.phase || 'chargeback',
        dispute_amount: payload.dispute_amount,
      });
      return res.data;
    } catch {
      // Fallback to /demo/simulate-dispute
      const res = await api.post<SimulateDisputeResponse>('/demo/simulate-dispute', payload);
      return res.data;
    }
  },
};
