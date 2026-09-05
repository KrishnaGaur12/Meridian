export interface Transaction {
  transaction_id: string;
  customer_id: string;
  merchant_id: string;
  amount: number;
  currency: string;
  timestamp: string;
  payment_method: string;
  merchant_category: string;
  transaction_country: string;
  transaction_status: string;
  transaction_hour: number;
  account_age_days: number;
  previous_chargebacks: number;
  device_type: string;
  is_international: number;
  is_high_risk_merchant: number;
  transaction_velocity_1h: number;
  transaction_velocity_24h: number;
  avg_transaction_amount_30d: number;
  has_active_simulated_dispute?: boolean;
}

export interface RiskAssessment {
  transaction_id: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  decision: 'ALLOW' | 'REVIEW' | 'BLOCK';
  model_version: string;
}
