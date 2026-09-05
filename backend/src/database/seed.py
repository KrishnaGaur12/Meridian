"""
Database Seeder for Razorpay AI Risk Manager.
Populates initial database records (including TXN_LIVE_001, DSP_LIVE_001, and scenario datasets)
if the database contains no transaction records.
"""

from sqlalchemy.orm import Session
from src.database.repository import (
    create_transaction, create_dispute, create_evidence, get_all_transactions
)
from src.utils.logger import get_logger

logger = get_logger("DatabaseSeeder")

def seed_database_if_empty(db: Session) -> None:
    """Seeds default transactions, disputes, and evidence if DB is currently empty."""
    existing_txs = get_all_transactions(db)
    if existing_txs:
        logger.info(f"Database already populated ({len(existing_txs)} transactions found). Skipping seed.")
        return

    logger.info("Database is empty. Initializing seed data...")

    # 1. Primary Live Sample Transaction & Dispute (TXN_LIVE_001 / DSP_LIVE_001)
    tx_live = create_transaction(db, {
        "transaction_id": "TXN_LIVE_001",
        "customer_id": "CUST_LIVE_001",
        "merchant_id": "MERCHANT_001",
        "amount": 4999.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "IN",
        "transaction_hour": 14,
        "account_age_days": 240,
        "previous_chargebacks": 0,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "avg_transaction_amount_30d": 4200.0,
        "payment": {
            "payment_id": "PAY_LIVE_001",
            "card_network": "visa",
            "last4": "4242",
            "auth_code": "AUTH_LIVE_001",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "ORD_LIVE_001",
            "product_description": "Wireless Noise Cancelling Headphones",
            "order_amount": 4999.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "FUL_LIVE_001",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD987654321",
                "shipped_at": "2026-08-16T10:00:00Z",
                "delivered_at": "2026-08-18T16:20:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })

    disp_live = create_dispute(db, {
        "dispute_id": "DSP_LIVE_001",
        "transaction_id": tx_live.transaction_id,
        "reason_code": "product_not_received",
        "reason_description": "Customer claims order was not received",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    create_evidence(db, {
        "evidence_id": "EVD_LIVE_001",
        "dispute_id": disp_live.dispute_id,
        "transaction_id": tx_live.transaction_id,
        "evidence_type": "delivery_confirmation",
        "title": "Delivery Confirmation",
        "description": "Courier proof of delivery signed on 2026-08-18",
        "verification_status": "AVAILABLE",
        "evidence_data": {
            "tracking_number": "BD987654321",
            "delivery_status": "DELIVERED",
            "delivered_at": "2026-08-18T16:20:00Z"
        }
    })

    # 2. Scenario 1 (Contest)
    tx_sc1 = create_transaction(db, {
        "transaction_id": "TXN_8001",
        "customer_id": "CUST_201",
        "merchant_id": "MERCH_101",
        "amount": 4500.0,
        "currency": "INR",
        "transaction_country": "IN",
        "account_age_days": 240,
        "order": {
            "order_id": "ORD_8001",
            "product_description": "Electronics Package",
            "fulfillment": {
                "fulfillment_id": "FUL_8001",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD123456",
                "shipped_at": "2026-08-11T09:00:00Z",
                "delivered_at": "2026-08-14T15:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })
    create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_01",
        "transaction_id": tx_sc1.transaction_id,
        "reason_code": "product_not_received",
        "reason_description": "Goods not received claim",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 3. Scenario 2 (Accept)
    tx_sc2 = create_transaction(db, {
        "transaction_id": "TXN_8002",
        "customer_id": "CUST_202",
        "merchant_id": "MERCH_102",
        "amount": 1800.0,
        "currency": "INR"
    })
    create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_02",
        "transaction_id": tx_sc2.transaction_id,
        "reason_code": "product_not_received",
        "reason_description": "Item missing, no tracking provided",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 4. Scenario 3 (Investigate)
    tx_sc3 = create_transaction(db, {
        "transaction_id": "TXN_8003",
        "customer_id": "CUST_203",
        "merchant_id": "MERCH_103",
        "amount": 12000.0,
        "currency": "INR",
        "order": {
            "order_id": "ORD_8003",
            "product_description": "Home Appliance",
            "fulfillment": {
                "fulfillment_id": "FUL_8003",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD999000",
                "shipped_at": "2026-08-13T10:00:00Z",
                "delivered_at": "2026-08-15T18:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })
    create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_03",
        "transaction_id": tx_sc3.transaction_id,
        "reason_code": "product_not_received",
        "reason_description": "Customer claims never received order",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 5. Scenario 4 (High Fraud)
    tx_sc4 = create_transaction(db, {
        "transaction_id": "TXN_8004",
        "customer_id": "CUST_204",
        "merchant_id": "MERCH_104",
        "amount": 95000.0,
        "currency": "INR",
        "is_international": 1,
        "is_high_risk_merchant": 1,
        "transaction_velocity_1h": 6,
        "transaction_velocity_24h": 12
    })
    create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_04",
        "transaction_id": tx_sc4.transaction_id,
        "reason_code": "fraudulent_transaction",
        "reason_description": "Card stolen unauthorized charge",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 6. Scenario 5 (Duplicate)
    tx_sc5 = create_transaction(db, {
        "transaction_id": "TXN_8005",
        "customer_id": "CUST_205",
        "merchant_id": "MERCH_105",
        "amount": 6500.0,
        "currency": "INR"
    })
    create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_05",
        "transaction_id": tx_sc5.transaction_id,
        "reason_code": "duplicate_charge",
        "reason_description": "Billed twice for same transaction",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 7. Additional Synthetic DSP_1001
    tx_9001 = create_transaction(db, {
        "transaction_id": "TXN_9001",
        "customer_id": "CUST_501",
        "merchant_id": "MERCH_801",
        "amount": 4999.0,
        "currency": "INR",
        "order": {
            "order_id": "ORD_9001",
            "product_description": "Smart Appliance",
            "fulfillment": {
                "fulfillment_id": "FUL_9001",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD987654",
                "shipped_at": "2026-08-16T09:00:00Z",
                "delivered_at": "2026-08-18T16:20:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })
    create_dispute(db, {
        "dispute_id": "DSP_1001",
        "transaction_id": tx_9001.transaction_id,
        "reason_code": "product_not_received",
        "reason_description": "Goods not received claim",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 8. Scenario 06 (Damaged Product - Needs Refund Proof)
    tx_sc6 = create_transaction(db, {
        "transaction_id": "TXN_8006",
        "customer_id": "CUST_206",
        "merchant_id": "MERCH_106",
        "amount": 8500.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "apparel",
        "account_age_days": 120,
        "payment": {
            "payment_id": "PAY_8006",
            "card_network": "mastercard",
            "last4": "8899",
            "auth_code": "AUTH_8006",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "ORD_8006",
            "product_description": "Designer Leather Jacket",
            "order_amount": 8500.0,
            "fulfillment": {
                "fulfillment_id": "FUL_8006",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD776655",
                "shipped_at": "2026-08-10T10:00:00Z",
                "delivered_at": "2026-08-13T14:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })
    create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_06",
        "transaction_id": tx_sc6.transaction_id,
        "reason_code": "product_unacceptable",
        "reason_description": "Customer claims jacket zipper arrived defective",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 9. Scenario 07 (Digital Subscription - Awaiting Merchant Review)
    tx_sc7 = create_transaction(db, {
        "transaction_id": "TXN_8007",
        "customer_id": "CUST_207",
        "merchant_id": "MERCH_107",
        "amount": 2499.0,
        "currency": "INR",
        "payment_method": "upi",
        "merchant_category": "digital_goods",
        "account_age_days": 365,
        "payment": {
            "payment_id": "PAY_8007",
            "card_network": "upi",
            "last4": "0000",
            "auth_code": "AUTH_8007",
            "payment_status": "CAPTURED"
        }
    })
    create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_07",
        "transaction_id": tx_sc7.transaction_id,
        "reason_code": "credit_not_processed",
        "reason_description": "Customer claims software renewal credit was promised but not posted",
        "status": "OPEN",
        "case_source": "DEMO"
    })

    # 10. Scenario 08 (High-Value Secured Transaction - Ready for Submission)
    tx_sc8 = create_transaction(db, {
        "transaction_id": "TXN_8008",
        "customer_id": "CUST_208",
        "merchant_id": "MERCH_108",
        "amount": 45000.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "account_age_days": 400,
        "is_international": 0,
        "payment": {
            "payment_id": "PAY_8008",
            "card_network": "visa",
            "last4": "1122",
            "auth_code": "AUTH_8008",
            "payment_status": "CAPTURED",
            "avs_match": "Y",
            "cvv_match": "M"
        },
        "order": {
            "order_id": "ORD_8008",
            "product_description": "4K Ultra HD Gaming Monitor",
            "fulfillment": {
                "fulfillment_id": "FUL_8008",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD443322",
                "shipped_at": "2026-08-05T09:00:00Z",
                "delivered_at": "2026-08-07T11:30:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })
    disp_sc8 = create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_08",
        "transaction_id": tx_sc8.transaction_id,
        "reason_code": "fraudulent_transaction",
        "reason_description": "Customer bank filed unauthorized charge claim",
        "status": "OPEN",
        "case_source": "DEMO"
    })
    create_evidence(db, {
        "evidence_id": "EVD_8008_1",
        "dispute_id": disp_sc8.dispute_id,
        "transaction_id": tx_sc8.transaction_id,
        "evidence_type": "customer_authentication",
        "title": "3DS 2.0 Strong Customer Authentication Log",
        "description": "Verified OTP & IP geolocation match cardholder registration",
        "verification_status": "AVAILABLE"
    })

    # 11. Scenario 09 (Express Courier Shipment - Submitted to Razorpay)
    tx_sc9 = create_transaction(db, {
        "transaction_id": "TXN_8009",
        "customer_id": "CUST_209",
        "merchant_id": "MERCH_109",
        "amount": 14200.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "account_age_days": 180,
        "order": {
            "order_id": "ORD_8009",
            "product_description": "High Performance Tablet",
            "fulfillment": {
                "fulfillment_id": "FUL_8009",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD112233",
                "shipped_at": "2026-08-12T08:00:00Z",
                "delivered_at": "2026-08-14T17:45:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })
    disp_sc9 = create_dispute(db, {
        "dispute_id": "DSP_SCENARIO_09",
        "transaction_id": tx_sc9.transaction_id,
        "reason_code": "product_not_received",
        "reason_description": "Customer claims tablet package not delivered",
        "status": "UNDER_REVIEW",
        "case_source": "DEMO"
    })
    create_evidence(db, {
        "evidence_id": "EVD_8009_1",
        "dispute_id": disp_sc9.dispute_id,
        "transaction_id": tx_sc9.transaction_id,
        "evidence_type": "delivery_confirmation",
        "title": "FedEx Express Proof of Delivery",
        "description": "Signed delivery receipt with recipient signature and GPS coordinate map",
        "verification_status": "AVAILABLE"
    })

    logger.info("Successfully seeded default transactions and disputes.")

