"""
Live Database Seeder for Razorpay AI Risk Manager.
Populates 15 deterministic, realistic live transaction records with full customer,
payment, order, and fulfillment context.
Initially contains ZERO disputes, ZERO evidence, and ZERO chargeback packages.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from src.database.models import (
    Customer, Transaction, Payment, Order, Fulfillment,
    Dispute, DisputeEvent, Evidence, ChargebackPackage, RiskAssessment
)
from src.database.repository import (
    get_all_transactions, create_customer, create_transaction,
    create_payment, create_order, create_fulfillment
)
from src.utils.logger import get_logger

logger = get_logger("LiveDatabaseSeeder")

LIVE_SEED_TRANSACTIONS: List[Dict[str, Any]] = [
    {
        "transaction_id": "txn_8aK9pL2xM4v1wQ",
        "customer_id": "cust_9bN2kL4xM7v1wP",
        "account_age_days": 320,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 4500.0,
        "amount": 4999.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "IN",
        "transaction_hour": 14,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_9xL2mK4pQ8v1wN",
            "card_network": "visa",
            "last4": "4242",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH892314",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_7bM9xL2pK4v1wQ",
            "product_description": "Sony WH-1000XM5 Noise Cancelling Headphones",
            "order_amount": 4999.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_6aK9pL2xM4v1wR",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD772910456IN",
                "shipped_at": "2026-08-20T10:30:00Z",
                "delivered_at": "2026-08-22T15:45:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_3mN8pL9xK2v4wR",
        "customer_id": "cust_4pK8mN2xL7v9wQ",
        "account_age_days": 180,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 2200.0,
        "amount": 2499.0,
        "currency": "INR",
        "payment_method": "upi",
        "merchant_category": "digital_goods",
        "transaction_country": "IN",
        "transaction_hour": 18,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 2,
        "payment": {
            "payment_id": "pay_5xK9mL2pQ4v8wN",
            "card_network": "upi",
            "last4": "0000",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH771029",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_2vK8pL9xM4n7wQ",
            "product_description": "Adobe Creative Cloud Annual Subscription",
            "order_amount": 2499.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_1xM9pL4vK8n2wQ",
                "shipping_status": "DELIVERED",
                "tracking_number": "DIGITAL_LIC_883012",
                "shipped_at": "2026-08-21T18:00:00Z",
                "delivered_at": "2026-08-21T18:01:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_7bK4mL9xP2v8wQ",
        "customer_id": "cust_1zL9pK2xM4v7wN",
        "account_age_days": 450,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 8900.0,
        "amount": 12499.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "apparel",
        "transaction_country": "IN",
        "transaction_hour": 11,
        "device_type": "desktop",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_2nL8pK4vM9x1wQ",
            "card_network": "mastercard",
            "last4": "8899",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH662910",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_9xK2pL4vM8n1wQ",
            "product_description": "Italian Leather Trench Coat - Size L",
            "order_amount": 12499.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_8nL4pK9vM2x7wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "FX992145870IN",
                "shipped_at": "2026-08-19T09:00:00Z",
                "delivered_at": "2026-08-21T14:30:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_4xL9pK2vM8n1wQ",
        "customer_id": "cust_6bM4nL9xK2v8wP",
        "account_age_days": 210,
        "verification_status": "VERIFIED",
        "country": "US",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 350.0,
        "amount": 399.0,
        "currency": "USD",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "US",
        "transaction_hour": 16,
        "device_type": "desktop",
        "is_international": 1,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_8vK2pL9xM4n7wQ",
            "card_network": "amex",
            "last4": "1005",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH118290",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_5mN8pK2vL4x9wQ",
            "product_description": "Mechanical Ergonomic Keyboard - Hot-Swappable",
            "order_amount": 399.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_4pK8mN2xL7v9wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "DHL882019485US",
                "shipped_at": "2026-08-18T14:00:00Z",
                "delivered_at": "2026-08-21T11:20:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_9vK2pL4nM8x1wQ",
        "customer_id": "cust_3nL8pK4vM9x2wQ",
        "account_age_days": 90,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 1200.0,
        "amount": 1499.0,
        "currency": "INR",
        "payment_method": "netbanking",
        "merchant_category": "retail",
        "transaction_country": "IN",
        "transaction_hour": 20,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_1xM9pL4vK8n3wQ",
            "card_network": "netbanking",
            "last4": "0000",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH559102",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_8nL4pK9vM2x1wQ",
            "product_description": "Organic Gourmet Tea Gift Hamper Set",
            "order_amount": 1499.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_7bM9xL2pK4v8wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "DL339102845IN",
                "shipped_at": "2026-08-22T08:00:00Z",
                "delivered_at": "2026-08-24T16:15:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_5pK8mN2xL7v9wQ",
        "customer_id": "cust_8vK2pL9xM4n1wQ",
        "account_age_days": 540,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 15000.0,
        "amount": 34999.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "IN",
        "transaction_hour": 15,
        "device_type": "desktop",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_7bM9xL2pK4v3wQ",
            "card_network": "visa",
            "last4": "5566",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH449012",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_4xL9pK2vM8n3wQ",
            "product_description": "Dell UltraSharp 27-inch 4K USB-C Hub Monitor",
            "order_amount": 34999.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_9vK2pL4nM8x3wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD990145821IN",
                "shipped_at": "2026-08-17T11:00:00Z",
                "delivered_at": "2026-08-19T13:40:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_2nL8pK4vM9x7wQ",
        "customer_id": "cust_5mN8pK2vL4x1wQ",
        "account_age_days": 150,
        "verification_status": "VERIFIED",
        "country": "GB",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 120.0,
        "amount": 185.0,
        "currency": "GBP",
        "payment_method": "credit_card",
        "merchant_category": "apparel",
        "transaction_country": "GB",
        "transaction_hour": 13,
        "device_type": "mobile",
        "is_international": 1,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_4pK8mN2xL7v1wQ",
            "card_network": "mastercard",
            "last4": "3344",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH992014",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_1xM9pL4vK8n7wQ",
            "product_description": "Waterproof Trail Running Shoes - UK 9",
            "order_amount": 185.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_5mN8pK2vL4x3wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "RM441029485GB",
                "shipped_at": "2026-08-21T10:00:00Z",
                "delivered_at": "2026-08-23T12:15:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_6aK9pL2xM4v8wR",
        "customer_id": "cust_7bM9xL2pK4v5wQ",
        "account_age_days": 380,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 6500.0,
        "amount": 7999.0,
        "currency": "INR",
        "payment_method": "upi",
        "merchant_category": "services",
        "transaction_country": "IN",
        "transaction_hour": 17,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_9vK2pL4nM8x5wQ",
            "card_network": "upi",
            "last4": "0000",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH331902",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_8vK2pL9xM4n5wQ",
            "product_description": "Full Vehicle Annual Maintenance & Ceramic Coating Package",
            "order_amount": 7999.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_2nL8pK4vM9x3wQ",
                "shipping_status": "DELIVERED",
                "tracking_number": "SVC_INV_771920",
                "shipped_at": "2026-08-20T09:00:00Z",
                "delivered_at": "2026-08-20T17:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_1xM9pL4vK8n5wQ",
        "customer_id": "cust_4xL9pK2vM8n7wQ",
        "account_age_days": 270,
        "verification_status": "VERIFIED",
        "country": "SG",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 600.0,
        "amount": 750.0,
        "currency": "SGD",
        "payment_method": "credit_card",
        "merchant_category": "hospitality",
        "transaction_country": "SG",
        "transaction_hour": 10,
        "device_type": "desktop",
        "is_international": 1,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_3mN8pL9xK2v1wR",
            "card_network": "visa",
            "last4": "9901",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH881920",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_6aK9pL2xM4v3wR",
            "product_description": "2-Night Luxury Boutique Hotel Stay Voucher",
            "order_amount": 750.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_1xM9pL4vK8n9wQ",
                "shipping_status": "DELIVERED",
                "tracking_number": "BOOKING_REF_SG9912",
                "shipped_at": "2026-08-16T10:00:00Z",
                "delivered_at": "2026-08-16T10:05:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_8vK2pL9xM4n9wQ",
        "customer_id": "cust_9vK2pL4nM8x7wQ",
        "account_age_days": 600,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 45000.0,
        "amount": 54999.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "IN",
        "transaction_hour": 19,
        "device_type": "desktop",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_5pK8mN2xL7v3wQ",
            "card_network": "visa",
            "last4": "1122",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH221940",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_3mN8pL9xK2v7wR",
            "product_description": "Apple iPad Pro 13-inch M4 Chip (Wi-Fi 256GB)",
            "order_amount": 54999.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_6aK9pL2xM4v7wR",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD441920491IN",
                "shipped_at": "2026-08-15T09:30:00Z",
                "delivered_at": "2026-08-17T14:10:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_7bM9xL2pK4v9wQ",
        "customer_id": "cust_2nL8pK4vM9x5wQ",
        "account_age_days": 110,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 3200.0,
        "amount": 3899.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "retail",
        "transaction_country": "IN",
        "transaction_hour": 12,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_6aK9pL2xM4v5wR",
            "card_network": "rupay",
            "last4": "7788",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH778901",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_7bK4mL9xP2v3wQ",
            "product_description": "Smart Air Purifier with HEPA Filter",
            "order_amount": 3899.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_3mN8pL9xK2v9wR",
                "shipping_status": "SHIPPED",
                "tracking_number": "DL881029384IN",
                "shipped_at": "2026-08-19T14:00:00Z",
                "delivered_at": "2026-08-22T10:50:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_5mN8pK2vL4x7wQ",
        "customer_id": "cust_1xM9pL4vK8n3wQ",
        "account_age_days": 240,
        "verification_status": "VERIFIED",
        "country": "AE",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 450.0,
        "amount": 550.0,
        "currency": "AED",
        "payment_method": "credit_card",
        "merchant_category": "apparel",
        "transaction_country": "AE",
        "transaction_hour": 14,
        "device_type": "mobile",
        "is_international": 1,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_7bK4mL9xP2v5wQ",
            "card_network": "mastercard",
            "last4": "2211",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH994820",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_9vK2pL4nM8x9wQ",
            "product_description": "Premium Chronograph Aviator Watch",
            "order_amount": 550.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_8vK2pL9xM4n3wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "ARMX77291039AE",
                "shipped_at": "2026-08-18T10:00:00Z",
                "delivered_at": "2026-08-21T15:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_3nL8pK4vM9x9wQ",
        "customer_id": "cust_6aK9pL2xM4v1wR",
        "account_age_days": 310,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 1900.0,
        "amount": 2199.0,
        "currency": "INR",
        "payment_method": "upi",
        "merchant_category": "dining",
        "transaction_country": "IN",
        "transaction_hour": 21,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 2,
        "payment": {
            "payment_id": "pay_8nL4pK9vM2x5wQ",
            "card_network": "upi",
            "last4": "0000",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH661902",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_4pK8mN2xL7v7wQ",
            "product_description": "Artisanal Bakery & Gourmet Coffee Catering Box",
            "order_amount": 2199.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_5pK8mN2xL7v5wQ",
                "shipping_status": "DELIVERED",
                "tracking_number": "SWIG_DEL_881920",
                "shipped_at": "2026-08-22T21:10:00Z",
                "delivered_at": "2026-08-22T21:40:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_4pK8mN2xL7v5wQ",
        "customer_id": "cust_8nL4pK9vM2x7wQ",
        "account_age_days": 410,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 7800.0,
        "amount": 9499.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "fitness",
        "transaction_country": "IN",
        "transaction_hour": 7,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_2vK8pL9xM4n9wQ",
            "card_network": "visa",
            "last4": "6677",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH119024",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_1zL9pK2xM4v9wN",
            "product_description": "Smart Indoor Cycling Trainer & Heart Rate Monitor",
            "order_amount": 9499.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_7bK4mL9xP2v7wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "BD661029482IN",
                "shipped_at": "2026-08-18T12:00:00Z",
                "delivered_at": "2026-08-20T16:30:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    },
    {
        "transaction_id": "txn_1zL9pK2xM4v5wN",
        "customer_id": "cust_3mN8pL9xK2v5wR",
        "account_age_days": 190,
        "verification_status": "VERIFIED",
        "country": "IN",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 11000.0,
        "amount": 14500.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "home",
        "transaction_country": "IN",
        "transaction_hour": 16,
        "device_type": "desktop",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 0,
        "transaction_velocity_24h": 1,
        "payment": {
            "payment_id": "pay_1zL9pK2xM4v7wN",
            "card_network": "mastercard",
            "last4": "4455",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH448910",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "order_5pK8mN2xL7v9wQ",
            "product_description": "Cordless Robotic Vacuum & Mop Cleaner",
            "order_amount": 14500.0,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "ful_9xK2pL4vM8n7wQ",
                "shipping_status": "SHIPPED",
                "tracking_number": "FX551029384IN",
                "shipped_at": "2026-08-17T15:00:00Z",
                "delivered_at": "2026-08-19T11:45:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }
]


def seed_live_database_if_empty(db: Session) -> None:
    """Seeds 15 realistic live transactions with 0 disputes into Live DB if empty."""
    existing_txs = get_all_transactions(db)
    if existing_txs:
        logger.info(f"Live database already populated ({len(existing_txs)} transactions found). Skipping seed.")
        return

    logger.info("Live database is empty. Initializing 15 clean live transactions...")

    for data in LIVE_SEED_TRANSACTIONS:
        # Create customer
        create_customer(db, {
            "customer_id": data["customer_id"],
            "account_age_days": data["account_age_days"],
            "verification_status": data["verification_status"],
            "country": data["country"],
            "previous_chargebacks": data["previous_chargebacks"],
            "avg_transaction_amount_30d": data["avg_transaction_amount_30d"]
        })

        # Create transaction
        create_transaction(db, {
            "transaction_id": data["transaction_id"],
            "customer_id": data["customer_id"],
            "merchant_id": "MERCHANT_LIVE_001",
            "amount": data["amount"],
            "currency": data["currency"],
            "payment_method": data["payment_method"],
            "merchant_category": data["merchant_category"],
            "transaction_country": data["transaction_country"],
            "transaction_hour": data["transaction_hour"],
            "device_type": data["device_type"],
            "is_international": data["is_international"],
            "is_high_risk_merchant": data["is_high_risk_merchant"],
            "transaction_velocity_1h": data["transaction_velocity_1h"],
            "transaction_velocity_24h": data["transaction_velocity_24h"],
            "avg_transaction_amount_30d": data["avg_transaction_amount_30d"],
            "payment": data.get("payment"),
            "order": data.get("order")
        })

    logger.info("Successfully seeded 15 clean live transactions with 0 disputes.")


def reset_live_database_seed(db: Session) -> None:
    """
    Clears all disputes, events, evidence, packages, and transactions from Live DB,
    and reseeds the 15 clean initial transactions.
    """
    logger.warning("Resetting Live Database to initial clean state...")
    db.query(ChargebackPackage).delete()
    db.query(Evidence).delete()
    db.query(DisputeEvent).delete()
    db.query(Dispute).delete()
    db.query(RiskAssessment).delete()
    db.query(Fulfillment).delete()
    db.query(Order).delete()
    db.query(Payment).delete()
    db.query(Transaction).delete()
    db.query(Customer).delete()
    db.commit()

    seed_live_database_if_empty(db)
    logger.info("Live Database reset complete.")
