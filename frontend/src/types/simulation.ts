export interface SimulateDisputePayload {
  transaction_id: string;
  reason_code: string;
  reason_description?: string;
  phase?: string;
  dispute_amount?: number;
}

export interface SimulationTransaction {
  transaction_id: string;
  customer_id: string;
  customer_name?: string;
  amount: number;
  currency: string;
  timestamp: string;
  payment_method: string;
  transaction_status: string;
  transaction_country?: string;
  country?: string;
  has_active_simulated_dispute?: boolean;
}
