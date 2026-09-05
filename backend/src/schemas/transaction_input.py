"""
Transaction Input Validation Schema — Fraud Detection Model V2.
Validates the 12 required transaction-level features for Fraud V2 prediction.
Rejects invalid/missing fields without inventing fake or default data.
"""

from typing import Dict, Any, Tuple, List, Optional
from src.utils.logger import get_logger

logger = get_logger("TransactionInputValidator")

# Required 12 transaction feature names
REQUIRED_V2_FEATURES = [
    "transaction_hour",
    "account_age_days",
    "previous_chargebacks",
    "merchant_category",
    "transaction_country",
    "device_type",
    "is_international",
    "is_high_risk_merchant",
    "transaction_amount",
    "transaction_velocity_1h",
    "transaction_velocity_24h",
    "avg_transaction_amount_30d"
]

def validate_transaction_input(payload: Dict[str, Any]) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """
    Validates payload against Fraud V2's 12 transaction-level features.
    
    Returns:
        (is_valid: bool, error_messages: List[str], validated_dict: Optional[Dict[str, Any]])
    """
    errors = []
    validated = {}
    
    if not isinstance(payload, dict):
        return False, [f"Input payload must be a JSON dictionary, got {type(payload).__name__}."], None

    # Helper mapping for compatible aliases if explicit V2 names are missing
    def get_field_val(primary_key: str, fallback_key: str = None):
        if primary_key in payload and payload[primary_key] is not None:
            return payload[primary_key]
        if fallback_key and fallback_key in payload and payload[fallback_key] is not None:
            return payload[fallback_key]
        return None

    # 1. transaction_hour (int 0..23)
    raw_hour = get_field_val("transaction_hour")
    if raw_hour is None and "transaction_timestamp" in payload:
        try:
            ts_str = str(payload["transaction_timestamp"])
            if "T" in ts_str:
                raw_hour = int(ts_str.split("T")[1].split(":")[0])
            elif " " in ts_str:
                raw_hour = int(ts_str.split(" ")[1].split(":")[0])
        except Exception:
            raw_hour = None
            
    if raw_hour is None:
        errors.append("Missing required transaction field: 'transaction_hour'.")
    elif isinstance(raw_hour, bool):
        errors.append("Invalid type for 'transaction_hour' (boolean). Must be an integer between 0 and 23.")
    else:
        try:
            h = int(raw_hour)
            if 0 <= h <= 23:
                validated["transaction_hour"] = h
            else:
                errors.append(f"Invalid 'transaction_hour' value ({raw_hour}). Must be between 0 and 23.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'transaction_hour' ({type(raw_hour).__name__}). Must be an integer between 0 and 23.")

    # 2. account_age_days (int >= 0)
    raw_age = get_field_val("account_age_days", "customer_account_age_days")
    if raw_age is None:
        errors.append("Missing required transaction field: 'account_age_days'.")
    elif isinstance(raw_age, bool):
        errors.append("Invalid type for 'account_age_days' (boolean). Must be a non-negative integer.")
    else:
        try:
            age = int(raw_age)
            if age >= 0:
                validated["account_age_days"] = age
            else:
                errors.append(f"Invalid 'account_age_days' value ({raw_age}). Must be >= 0.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'account_age_days' ({type(raw_age).__name__}). Must be a non-negative integer.")

    # 3. previous_chargebacks (int >= 0)
    raw_cb = get_field_val("previous_chargebacks", "customer_dispute_count")
    if raw_cb is None:
        errors.append("Missing required transaction field: 'previous_chargebacks'.")
    elif isinstance(raw_cb, bool):
        errors.append("Invalid type for 'previous_chargebacks' (boolean). Must be a non-negative integer.")
    else:
        try:
            cb = int(raw_cb)
            if cb >= 0:
                validated["previous_chargebacks"] = cb
            else:
                errors.append(f"Invalid 'previous_chargebacks' value ({raw_cb}). Must be >= 0.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'previous_chargebacks' ({type(raw_cb).__name__}). Must be a non-negative integer.")

    # 4. merchant_category (non-empty string)
    raw_cat = get_field_val("merchant_category")
    if raw_cat is None:
        errors.append("Missing required transaction field: 'merchant_category'.")
    elif not isinstance(raw_cat, str) or not raw_cat.strip():
        errors.append(f"Invalid 'merchant_category' ({raw_cat}). Must be a non-empty string.")
    else:
        validated["merchant_category"] = raw_cat.strip().lower()

    # 5. transaction_country (non-empty string)
    raw_country = get_field_val("transaction_country")
    if raw_country is None:
        errors.append("Missing required transaction field: 'transaction_country'.")
    elif not isinstance(raw_country, str) or not raw_country.strip():
        errors.append(f"Invalid 'transaction_country' ({raw_country}). Must be a non-empty string.")
    else:
        validated["transaction_country"] = raw_country.strip().upper()

    # 6. device_type (non-empty string)
    raw_device = get_field_val("device_type")
    if raw_device is None:
        errors.append("Missing required transaction field: 'device_type'.")
    elif not isinstance(raw_device, str) or not raw_device.strip():
        errors.append(f"Invalid 'device_type' ({raw_device}). Must be a non-empty string.")
    else:
        validated["device_type"] = raw_device.strip().lower()

    # 7. is_international (binary 0 or 1)
    raw_intl = get_field_val("is_international", "ip_billing_mismatch")
    if raw_intl is None:
        errors.append("Missing required transaction field: 'is_international'.")
    elif isinstance(raw_intl, bool):
        validated["is_international"] = 1 if raw_intl else 0
    else:
        try:
            intl = int(raw_intl)
            if intl in (0, 1):
                validated["is_international"] = intl
            else:
                errors.append(f"Invalid 'is_international' value ({raw_intl}). Must be 0 or 1.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'is_international' ({type(raw_intl).__name__}). Must be 0 or 1.")

    # 8. is_high_risk_merchant (binary 0 or 1)
    raw_hrm = get_field_val("is_high_risk_merchant", "merchant_high_risk_flag")
    if raw_hrm is None:
        errors.append("Missing required transaction field: 'is_high_risk_merchant'.")
    elif isinstance(raw_hrm, bool):
        validated["is_high_risk_merchant"] = 1 if raw_hrm else 0
    else:
        try:
            hrm = int(raw_hrm)
            if hrm in (0, 1):
                validated["is_high_risk_merchant"] = hrm
            else:
                errors.append(f"Invalid 'is_high_risk_merchant' value ({raw_hrm}). Must be 0 or 1.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'is_high_risk_merchant' ({type(raw_hrm).__name__}). Must be 0 or 1.")

    # 9. transaction_amount (float > 0)
    raw_amt = get_field_val("transaction_amount")
    if raw_amt is None:
        errors.append("Missing required transaction field: 'transaction_amount'.")
    elif isinstance(raw_amt, bool):
        errors.append("Invalid type for 'transaction_amount' (boolean). Must be a positive number.")
    else:
        try:
            amt = float(raw_amt)
            if amt > 0.0:
                validated["transaction_amount"] = amt
            else:
                errors.append(f"Invalid 'transaction_amount' value ({raw_amt}). Must be > 0.0.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'transaction_amount' ({type(raw_amt).__name__}). Must be a positive number.")

    # 10. transaction_velocity_1h (int >= 0)
    raw_v1 = get_field_val("transaction_velocity_1h")
    if raw_v1 is None:
        errors.append("Missing required transaction field: 'transaction_velocity_1h'.")
    elif isinstance(raw_v1, bool):
        errors.append("Invalid type for 'transaction_velocity_1h' (boolean). Must be a non-negative integer.")
    else:
        try:
            v1 = int(raw_v1)
            if v1 >= 0:
                validated["transaction_velocity_1h"] = v1
            else:
                errors.append(f"Invalid 'transaction_velocity_1h' value ({raw_v1}). Must be >= 0.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'transaction_velocity_1h' ({type(raw_v1).__name__}). Must be a non-negative integer.")

    # 11. transaction_velocity_24h (int >= 0)
    raw_v24 = get_field_val("transaction_velocity_24h", "dispute_velocity_24h")
    if raw_v24 is None:
        errors.append("Missing required transaction field: 'transaction_velocity_24h'.")
    elif isinstance(raw_v24, bool):
        errors.append("Invalid type for 'transaction_velocity_24h' (boolean). Must be a non-negative integer.")
    else:
        try:
            v24 = int(raw_v24)
            if v24 >= 0:
                validated["transaction_velocity_24h"] = v24
            else:
                errors.append(f"Invalid 'transaction_velocity_24h' value ({raw_v24}). Must be >= 0.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'transaction_velocity_24h' ({type(raw_v24).__name__}). Must be a non-negative integer.")

    # 12. avg_transaction_amount_30d (float > 0)
    raw_avg = get_field_val("avg_transaction_amount_30d", "customer_avg_amount")
    if raw_avg is None:
        errors.append("Missing required transaction field: 'avg_transaction_amount_30d'.")
    elif isinstance(raw_avg, bool):
        errors.append("Invalid type for 'avg_transaction_amount_30d' (boolean). Must be a positive number.")
    else:
        try:
            avg = float(raw_avg)
            if avg > 0.0:
                validated["avg_transaction_amount_30d"] = avg
            else:
                errors.append(f"Invalid 'avg_transaction_amount_30d' value ({raw_avg}). Must be > 0.0.")
        except (ValueError, TypeError):
            errors.append(f"Invalid type for 'avg_transaction_amount_30d' ({type(raw_avg).__name__}). Must be a positive number.")

    if errors:
        return False, errors, None
        
    return True, [], validated
