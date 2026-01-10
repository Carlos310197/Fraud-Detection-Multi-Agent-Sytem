"""Data loader for transactions, customer behavior, and fraud policies."""
import csv
import json
from pathlib import Path

from app.api.schemas import (
    Transaction,
    CustomerBehavior,
    FraudPolicy,
    ConsolidatedTransaction,
)
from app.core.errors import DataLoadError, CustomerNotFoundError
from app.core.logging import logger


def load_transactions(path: str | Path) -> dict[str, Transaction]:
    """
    Load transactions from a CSV file.
    
    Args:
        path: Path to the transactions CSV file
        
    Returns:
        Dictionary mapping transaction_id to Transaction
    """
    transactions: dict[str, Transaction] = {}
    path = Path(path)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txn = Transaction(
                    transaction_id=row["transaction_id"],
                    customer_id=row["customer_id"],
                    amount=float(row["amount"]),
                    currency=row["currency"],
                    country=row["country"],
                    channel=row["channel"],
                    device_id=row["device_id"],
                    timestamp=row["timestamp"],
                    merchant_id=row["merchant_id"],
                )
                transactions[txn.transaction_id] = txn
        
        logger.info(f"Loaded {len(transactions)} transactions from {path}")
        return transactions
    
    except Exception as e:
        raise DataLoadError(str(path), str(e))


def load_customer_behavior(path: str | Path) -> dict[str, CustomerBehavior]:
    """
    Load customer behavior profiles from a CSV file.
    
    Normalizes:
    - usual_countries: string to list
    - usual_devices: string to list
    
    Args:
        path: Path to the customer_behavior CSV file
        
    Returns:
        Dictionary mapping customer_id to CustomerBehavior
    """
    customers: dict[str, CustomerBehavior] = {}
    path = Path(path)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize countries to list
                countries_raw = row["usual_countries"]
                if isinstance(countries_raw, str):
                    # Handle comma-separated or single value
                    countries = [c.strip() for c in countries_raw.split(",") if c.strip()]
                else:
                    countries = countries_raw
                
                # Normalize devices to list
                devices_raw = row["usual_devices"]
                if isinstance(devices_raw, str):
                    devices = [d.strip() for d in devices_raw.split(",") if d.strip()]
                else:
                    devices = devices_raw
                
                customer = CustomerBehavior(
                    customer_id=row["customer_id"],
                    usual_amount_avg=float(row["usual_amount_avg"]),
                    usual_hours=row["usual_hours"],
                    usual_countries=countries,
                    usual_devices=devices,
                )
                customers[customer.customer_id] = customer
        
        logger.info(f"Loaded {len(customers)} customer profiles from {path}")
        return customers
    
    except Exception as e:
        raise DataLoadError(str(path), str(e))


def load_policies(path: str | Path) -> list[FraudPolicy]:
    """
    Load fraud policies from a JSON file.
    
    Args:
        path: Path to the fraud_policies JSON file
        
    Returns:
        List of FraudPolicy objects
    """
    path = Path(path)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        policies = [FraudPolicy(**p) for p in data]
        logger.info(f"Loaded {len(policies)} fraud policies from {path}")
        return policies
    
    except Exception as e:
        raise DataLoadError(str(path), str(e))


def parse_hours(hours_str: str) -> tuple[int, int]:
    """
    Parse hours string (e.g., '08-20') to (start, end) tuple.
    
    Args:
        hours_str: Hours string in format 'HH-HH'
        
    Returns:
        Tuple of (start_hour, end_hour)
    """
    try:
        parts = hours_str.split("-")
        start = int(parts[0])
        end = int(parts[1])
        return start, end
    except (IndexError, ValueError):
        # Default to business hours if parsing fails
        return 8, 20


def consolidate(
    transaction_id: str,
    transactions: dict[str, Transaction],
    customers: dict[str, CustomerBehavior],
) -> ConsolidatedTransaction:
    """
    Consolidate transaction with customer behavior data.
    
    Args:
        transaction_id: ID of the transaction to consolidate
        transactions: Dictionary of all transactions
        customers: Dictionary of all customer behaviors
        
    Returns:
        ConsolidatedTransaction with merged data
    """
    from app.core.errors import TransactionNotFoundError
    
    if transaction_id not in transactions:
        raise TransactionNotFoundError(transaction_id)
    
    txn = transactions[transaction_id]
    
    if txn.customer_id not in customers:
        raise CustomerNotFoundError(txn.customer_id)
    
    customer = customers[txn.customer_id]
    hours_start, hours_end = parse_hours(customer.usual_hours)
    
    return ConsolidatedTransaction(
        transaction_id=txn.transaction_id,
        customer_id=txn.customer_id,
        amount=txn.amount,
        currency=txn.currency,
        country=txn.country,
        channel=txn.channel,
        device_id=txn.device_id,
        timestamp=txn.timestamp,
        merchant_id=txn.merchant_id,
        usual_amount_avg=customer.usual_amount_avg,
        usual_hours_start=hours_start,
        usual_hours_end=hours_end,
        usual_countries=customer.usual_countries,
        usual_devices=customer.usual_devices,
    )
