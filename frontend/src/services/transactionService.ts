import { api } from './api';
import { Transaction, RiskAssessment } from '../types/transaction';

export const transactionService = {
  async getTransactions(): Promise<Transaction[]> {
    const res = await api.get<Transaction[]>('/transactions');
    return res.data;
  },

  async getTransactionById(transactionId: string): Promise<Transaction> {
    const res = await api.get<Transaction>(`/transactions/${transactionId}`);
    return res.data;
  },

  async runRiskAssessment(transactionId: string): Promise<RiskAssessment> {
    const res = await api.post<RiskAssessment>(`/transactions/${transactionId}/risk-assessment`);
    return res.data;
  },
};
