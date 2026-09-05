"""
Synthetic Data Generator & Scenario Factory for Razorpay AI Risk Manager.
Generates realistic, domain-grounded dispute & transaction datasets for ML training
and creates 5 distinct scenario JSON files for testing and CLI demonstration.
"""

from typing import Dict, List
import json
import random
import numpy as np
import pandas as pd
from pathlib import Path
from config.settings import SYNTHETIC_DATA_DIR, DisputeReason

def generate_fraud_dataset(n_samples: int = 2000, random_state: int = 42) -> pd.DataFrame:
    """
    Generates realistic synthetic transaction/dispute dataset for Fraud Detection Model benchmarking.
    Incorporate key risk features: amount deviation, velocity 24h & 7d, account age, risk flags.
    """
    np.random.seed(random_state)
    random.seed(random_state)
    
    # 1. Base Transaction Features
    tx_amounts = np.random.exponential(scale=3500, size=n_samples) + 150.0  # INR
    tx_amounts = np.round(tx_amounts, 2)
    
    # Customer baseline average transaction amount
    cust_avg_amounts = np.round(tx_amounts * np.random.uniform(0.4, 1.8, size=n_samples), 2)
    amount_deviation_ratio = np.round(tx_amounts / np.maximum(cust_avg_amounts, 50.0), 4)
    
    dispute_amounts = np.round(tx_amounts * np.random.uniform(0.85, 1.0, size=n_samples), 2)
    
    customer_dispute_counts = np.random.poisson(lam=0.4, size=n_samples)
    merchant_dispute_rates = np.random.beta(a=1.5, b=45.0, size=n_samples) # ~3% avg
    
    days_since_payment = np.random.randint(1, 90, size=n_samples)
    dispute_velocity_24h = np.random.poisson(lam=0.25, size=n_samples)
    dispute_velocity_7d = dispute_velocity_24h + np.random.poisson(lam=0.6, size=n_samples)
    
    is_duplicate_flag = np.random.choice([0, 1], p=[0.93, 0.07], size=n_samples)
    transaction_hours = np.random.randint(0, 24, size=n_samples)
    transaction_days = np.random.randint(0, 7, size=n_samples)
    
    reason_codes = np.random.choice([0, 1, 2, 3, 4, 5], p=[0.35, 0.20, 0.25, 0.08, 0.07, 0.05], size=n_samples)
    merchant_high_risk = np.random.choice([0, 1], p=[0.88, 0.12], size=n_samples)
    customer_account_age = np.random.randint(1, 730, size=n_samples)
    ip_billing_mismatch = np.random.choice([0, 1], p=[0.90, 0.10], size=n_samples)

    # 2. Domain Risk Score (Non-linear combination)
    risk_score = (
        (amount_deviation_ratio > 2.5).astype(int) * 0.75 +
        (dispute_velocity_24h >= 2).astype(int) * 0.90 +
        (dispute_velocity_7d >= 4).astype(int) * 0.60 +
        (customer_dispute_counts >= 3).astype(int) * 0.85 +
        (merchant_dispute_rates > 0.04).astype(int) * 0.70 +
        (customer_account_age < 15).astype(int) * 0.80 +
        (days_since_payment <= 1).astype(int) * 0.65 +
        is_duplicate_flag * 1.10 +
        np.isin(transaction_hours, [1, 2, 3, 4]).astype(int) * 0.50 +
        (reason_codes == 2).astype(int) * 0.60 + # UNAUTHORIZED
        merchant_high_risk * 0.80 +
        ip_billing_mismatch * 0.95 - 2.20
    )
    
    fraud_prob = 1.0 / (1.0 + np.exp(-risk_score))
    # Add modest label noise for realistic overlap
    noisy_prob = np.clip(fraud_prob + np.random.normal(0, 0.05, size=n_samples), 0.01, 0.99)
    is_fraud = (np.random.uniform(0, 1, size=n_samples) < noisy_prob).astype(int)
    
    df = pd.DataFrame({
        "transaction_amount": tx_amounts,
        "customer_avg_amount": cust_avg_amounts,
        "amount_deviation_ratio": amount_deviation_ratio,
        "dispute_amount": dispute_amounts,
        "customer_dispute_count": customer_dispute_counts,
        "merchant_dispute_rate": np.round(merchant_dispute_rates, 4),
        "days_since_payment": days_since_payment,
        "dispute_velocity_24h": dispute_velocity_24h,
        "dispute_velocity_7d": dispute_velocity_7d,
        "is_duplicate_flag": is_duplicate_flag,
        "transaction_hour": transaction_hours,
        "transaction_day_of_week": transaction_days,
        "reason_code_encoded": reason_codes,
        "merchant_high_risk_flag": merchant_high_risk,
        "customer_account_age_days": customer_account_age,
        "ip_billing_mismatch": ip_billing_mismatch,
        "is_fraud": is_fraud
    })
    
    return df


def generate_win_probability_dataset(n_samples: int = 2000, random_state: int = 42) -> pd.DataFrame:
    """
    Generates realistic synthetic evidence & dispute features for Win Probability Model benchmarking.
    Includes non-linear document interactions and missing proof penalties.
    """
    np.random.seed(random_state)
    random.seed(random_state)
    
    reason_codes = np.random.choice([0, 1, 2, 3, 4, 5], p=[0.35, 0.20, 0.25, 0.08, 0.07, 0.05], size=n_samples)
    has_invoice = np.random.choice([0, 1], p=[0.12, 0.88], size=n_samples)
    has_shipping_proof = np.random.choice([0, 1], p=[0.30, 0.70], size=n_samples)
    has_proof_of_delivery = np.random.choice([0, 1], p=[0.38, 0.62], size=n_samples)
    has_customer_comm = np.random.choice([0, 1], p=[0.45, 0.55], size=n_samples)
    
    completeness = np.round((has_invoice + has_shipping_proof + has_proof_of_delivery + has_customer_comm) / 4.0, 2)
    evidence_quality = np.clip(completeness * np.random.uniform(0.65, 1.0, size=n_samples), 0.1, 1.0)
    
    contradiction_count = np.random.poisson(lam=0.35, size=n_samples)
    contradiction_max_severity = np.clip(contradiction_count * np.random.choice([0, 1, 2, 3], size=n_samples), 0, 3)
    
    fraud_prob = np.random.beta(a=1.5, b=5.0, size=n_samples)
    merchant_win_rate = np.random.beta(a=5, b=2.5, size=n_samples)
    prev_won_count = np.random.randint(0, 50, size=n_samples)
    dispute_amounts = np.round(np.random.exponential(scale=3500, size=n_samples) + 100, 2)
    
    # Non-linear Win Logit Formula
    # Hard Penalty: Missing POD in GOODS_NOT_RECEIVED (code 0) severely reduces win chance
    pod_penalty = np.where((reason_codes == 0) & (has_proof_of_delivery == 0), -2.2, 0.0)
    
    win_logit = (
        completeness * 2.8 +
        evidence_quality * 1.8 +
        has_proof_of_delivery * 1.4 +
        has_invoice * 0.9 +
        has_customer_comm * 0.7 +
        pod_penalty -
        contradiction_count * 1.2 -
        contradiction_max_severity * 0.7 -
        fraud_prob * 2.4 +
        merchant_win_rate * 1.3 - 1.8
    )
    
    win_prob = 1.0 / (1.0 + np.exp(-win_logit))
    noisy_win_prob = np.clip(win_prob + np.random.normal(0, 0.04, size=n_samples), 0.01, 0.99)
    merchant_won = (np.random.uniform(0, 1, size=n_samples) < noisy_win_prob).astype(int)
    
    df = pd.DataFrame({
        "reason_code_encoded": reason_codes,
        "evidence_completeness_score": completeness,
        "has_invoice": has_invoice,
        "has_shipping_proof": has_shipping_proof,
        "has_proof_of_delivery": has_proof_of_delivery,
        "has_customer_communication": has_customer_comm,
        "contradiction_count": contradiction_count,
        "contradiction_max_severity": contradiction_max_severity,
        "fraud_probability": np.round(fraud_prob, 4),
        "merchant_historical_win_rate": np.round(merchant_win_rate, 4),
        "previous_disputes_won_count": prev_won_count,
        "dispute_amount": dispute_amounts,
        "evidence_quality_score": np.round(evidence_quality, 4),
        "merchant_won": merchant_won
    })
    
    return df


def generate_scenario_files() -> Dict[str, Path]:
    """
    Creates 5 realistic synthetic scenario JSON files representing key risk manager use-cases.
    """
    SYNTHETIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    scenarios = {
        "scenario_1_contest": {
            "dispute_id": "DSP_SCENARIO_01",
            "transaction_id": "TXN_8001",
            "merchant_id": "MERCH_101",
            "customer_id": "CUST_201",
            "dispute_reason": "GOODS_NOT_RECEIVED",
            "transaction_hour": 11,
            "account_age_days": 240,
            "previous_chargebacks": 0,
            "merchant_category": "retail",
            "transaction_country": "IN",
            "device_type": "mobile",
            "is_international": 0,
            "is_high_risk_merchant": 0,
            "transaction_amount": 4500.00,
            "transaction_velocity_1h": 0,
            "transaction_velocity_24h": 0,
            "avg_transaction_amount_30d": 4200.00,
            "dispute_amount": 4500.00,
            "customer_avg_amount": 4200.00,
            "transaction_timestamp": "2026-08-10T11:00:00",
            "dispute_timestamp": "2026-08-20T14:30:00",
            "customer_dispute_count": 0,
            "merchant_dispute_rate": 0.008,
            "merchant_historical_win_rate": 0.82,
            "previous_disputes_won_count": 18,
            "dispute_velocity_24h": 0,
            "dispute_velocity_7d": 0,
            "is_duplicate_flag": 0,
            "merchant_high_risk_flag": 0,
            "customer_account_age_days": 240,
            "ip_billing_mismatch": 0,
            "merchant_claim": "Order delivered via Bluedart tracking BD123456.",
            "customer_claim": "Standard billing query.",
            "available_evidence": [
                {
                    "document_id": "DOC_INV_101",
                    "document_type": "invoice",
                    "content": "Invoice #INV-8001 for Customer CUST_201 Amount 4500 INR.",
                    "order_id": "TXN_8001",
                    "customer_id": "CUST_201",
                    "dispute_id": "DSP_SCENARIO_01",
                    "timestamp": "2026-08-10T11:00:00",
                    "readability": 0.98,
                    "relevance": 1.0
                },
                {
                    "document_id": "DOC_SHP_101",
                    "document_type": "shipping_proof",
                    "content": "Bluedart Courier Tracking BD123456 shipped to CUST_201 address.",
                    "order_id": "TXN_8001",
                    "customer_id": "CUST_201",
                    "dispute_id": "DSP_SCENARIO_01",
                    "timestamp": "2026-08-11T09:00:00",
                    "readability": 0.95,
                    "relevance": 1.0
                },
                {
                    "document_id": "DOC_POD_101",
                    "document_type": "proof_of_delivery",
                    "content": "Proof of delivery signed by CUST_201 on 2026-08-14.",
                    "order_id": "TXN_8001",
                    "customer_id": "CUST_201",
                    "dispute_id": "DSP_SCENARIO_01",
                    "timestamp": "2026-08-14T15:00:00",
                    "readability": 0.99,
                    "relevance": 1.0
                }
            ]
        },
        "scenario_2_accept": {
            "dispute_id": "DSP_SCENARIO_02",
            "transaction_id": "TXN_8002",
            "merchant_id": "MERCH_102",
            "customer_id": "CUST_202",
            "dispute_reason": "GOODS_NOT_RECEIVED",
            "transaction_hour": 10,
            "account_age_days": 180,
            "previous_chargebacks": 0,
            "merchant_category": "retail",
            "transaction_country": "IN",
            "device_type": "mobile",
            "is_international": 0,
            "is_high_risk_merchant": 0,
            "transaction_amount": 1800.00,
            "transaction_velocity_1h": 0,
            "transaction_velocity_24h": 0,
            "avg_transaction_amount_30d": 1900.00,
            "dispute_amount": 1800.00,
            "customer_avg_amount": 1900.00,
            "transaction_timestamp": "2026-08-01T10:00:00",
            "dispute_timestamp": "2026-08-25T16:00:00",
            "customer_dispute_count": 0,
            "merchant_dispute_rate": 0.015,
            "merchant_historical_win_rate": 0.40,
            "previous_disputes_won_count": 2,
            "dispute_velocity_24h": 0,
            "dispute_velocity_7d": 0,
            "is_duplicate_flag": 0,
            "merchant_high_risk_flag": 0,
            "customer_account_age_days": 180,
            "ip_billing_mismatch": 0,
            "merchant_claim": "Goods dispatched standard post.",
            "customer_claim": "Items missing, no tracking provided.",
            "available_evidence": [
                {
                    "document_id": "DOC_INV_102",
                    "document_type": "invoice",
                    "content": "Invoice #INV-8002 for CUST_202.",
                    "order_id": "TXN_8002",
                    "customer_id": "CUST_202",
                    "dispute_id": "DSP_SCENARIO_02",
                    "timestamp": "2026-08-01T10:00:00",
                    "readability": 0.90,
                    "relevance": 0.85
                }
            ]
        },
        "scenario_3_investigate": {
            "dispute_id": "DSP_SCENARIO_03",
            "transaction_id": "TXN_8003",
            "merchant_id": "MERCH_103",
            "customer_id": "CUST_203",
            "dispute_reason": "GOODS_NOT_RECEIVED",
            "transaction_hour": 14,
            "account_age_days": 90,
            "previous_chargebacks": 1,
            "merchant_category": "electronics",
            "transaction_country": "IN",
            "device_type": "desktop",
            "is_international": 0,
            "is_high_risk_merchant": 0,
            "transaction_amount": 12000.00,
            "transaction_velocity_1h": 0,
            "transaction_velocity_24h": 0,
            "avg_transaction_amount_30d": 11000.00,
            "dispute_amount": 12000.00,
            "customer_avg_amount": 11000.00,
            "transaction_timestamp": "2026-08-12T14:00:00",
            "dispute_timestamp": "2026-08-22T10:00:00",
            "customer_dispute_count": 1,
            "merchant_dispute_rate": 0.020,
            "merchant_historical_win_rate": 0.65,
            "previous_disputes_won_count": 9,
            "dispute_velocity_24h": 0,
            "dispute_velocity_7d": 1,
            "is_duplicate_flag": 0,
            "merchant_high_risk_flag": 0,
            "customer_account_age_days": 90,
            "ip_billing_mismatch": 0,
            "merchant_claim": "Delivered to address on 15-Aug.",
            "customer_claim": "I never received the order.",
            "available_evidence": [
                {
                    "document_id": "DOC_INV_103",
                    "document_type": "invoice",
                    "content": "Invoice for ORD_8003.",
                    "order_id": "TXN_8003",
                    "customer_id": "CUST_203",
                    "dispute_id": "DSP_SCENARIO_03",
                    "timestamp": "2026-08-12T14:00:00",
                    "readability": 0.92,
                    "relevance": 1.0
                },
                {
                    "document_id": "DOC_POD_103",
                    "document_type": "proof_of_delivery",
                    "content": "POD slip signed by security guard on 2026-08-15.",
                    "order_id": "TXN_8003",
                    "customer_id": "CUST_203",
                    "dispute_id": "DSP_SCENARIO_03",
                    "timestamp": "2026-08-15T18:00:00",
                    "readability": 0.95,
                    "relevance": 1.0
                }
            ]
        },
        "scenario_4_high_fraud": {
            "dispute_id": "DSP_SCENARIO_04",
            "transaction_id": "TXN_8004",
            "merchant_id": "MERCH_104",
            "customer_id": "CUST_204",
            "dispute_reason": "UNAUTHORIZED_TRANSACTION",
            "transaction_hour": 3,
            "account_age_days": 1,
            "previous_chargebacks": 8,
            "merchant_category": "online_services",
            "transaction_country": "CA",
            "device_type": "tablet",
            "is_international": 1,
            "is_high_risk_merchant": 1,
            "transaction_amount": 95000.00,
            "transaction_velocity_1h": 6,
            "transaction_velocity_24h": 12,
            "avg_transaction_amount_30d": 1500.00,
            "dispute_amount": 95000.00,
            "customer_avg_amount": 1500.00,
            "transaction_timestamp": "2026-08-28T03:15:00",
            "dispute_timestamp": "2026-08-28T04:00:00",
            "customer_dispute_count": 8,
            "merchant_dispute_rate": 0.12,
            "merchant_historical_win_rate": 0.20,
            "previous_disputes_won_count": 0,
            "dispute_velocity_24h": 6,
            "dispute_velocity_7d": 12,
            "is_duplicate_flag": 1,
            "merchant_high_risk_flag": 1,
            "customer_account_age_days": 1,
            "ip_billing_mismatch": 1,
            "merchant_claim": "Automated order.",
            "customer_claim": "Card stolen. Unauthorized charge.",
            "available_evidence": []
        },
        "scenario_5_duplicate": {
            "dispute_id": "DSP_SCENARIO_05",
            "transaction_id": "TXN_8005",
            "merchant_id": "MERCH_105",
            "customer_id": "CUST_205",
            "dispute_reason": "DUPLICATE_TRANSACTION",
            "transaction_hour": 12,
            "account_age_days": 120,
            "previous_chargebacks": 0,
            "merchant_category": "retail",
            "transaction_country": "IN",
            "device_type": "mobile",
            "is_international": 0,
            "is_high_risk_merchant": 0,
            "transaction_amount": 6500.00,
            "transaction_velocity_1h": 1,
            "transaction_velocity_24h": 1,
            "avg_transaction_amount_30d": 6500.00,
            "dispute_amount": 6500.00,
            "customer_avg_amount": 6500.00,
            "transaction_timestamp": "2026-08-20T12:00:00",
            "dispute_timestamp": "2026-08-21T09:00:00",
            "customer_dispute_count": 0,
            "merchant_dispute_rate": 0.010,
            "merchant_historical_win_rate": 0.70,
            "previous_disputes_won_count": 8,
            "dispute_velocity_24h": 1,
            "dispute_velocity_7d": 1,
            "is_duplicate_flag": 1,
            "merchant_high_risk_flag": 0,
            "customer_account_age_days": 120,
            "ip_billing_mismatch": 0,
            "merchant_claim": "Single purchase processed.",
            "customer_claim": "Billed twice for same transaction.",
            "available_evidence": [
                {
                    "document_id": "DOC_INV_105",
                    "document_type": "invoice",
                    "content": "Invoice #INV-8005 Amount 6500 INR.",
                    "order_id": "TXN_8005",
                    "customer_id": "CUST_205",
                    "dispute_id": "DSP_SCENARIO_05",
                    "timestamp": "2026-08-20T12:00:00",
                    "readability": 0.95,
                    "relevance": 1.0
                }
            ]
        }
    }
    
    created_paths = {}
    for key, payload in scenarios.items():
        path = SYNTHETIC_DATA_DIR / f"{key}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        created_paths[key] = path
        
    return created_paths
