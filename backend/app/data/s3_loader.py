"""S3-based data loader for AWS deployment."""
import csv
import json
import io
import os
from typing import BinaryIO

import boto3

from app.api.schemas import Transaction, CustomerBehavior, FraudPolicy
from app.core.errors import DataLoadError
from app.core.logging import logger


def get_s3_client():
    """Get S3 client with proper configuration."""
    region = os.getenv("AWS_REGION", "us-east-1")
    return boto3.client("s3", region_name=region)


def load_transactions_from_s3(bucket: str, key: str = "transactions.csv") -> dict[str, Transaction]:
    """
    Load transactions from S3 bucket.
    
    Args:
        bucket: S3 bucket name
        key: Object key (default: transactions.csv)
        
    Returns:
        Dictionary mapping transaction_id to Transaction
    """
    transactions: dict[str, Transaction] = {}
    
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        
        reader = csv.DictReader(io.StringIO(content))
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
        
        logger.info(f"Loaded {len(transactions)} transactions from s3://{bucket}/{key}")
        return transactions
    
    except Exception as e:
        raise DataLoadError(f"s3://{bucket}/{key}", str(e))


def load_customer_behavior_from_s3(bucket: str, key: str = "customer_behavior.csv") -> dict[str, CustomerBehavior]:
    """
    Load customer behavior from S3 bucket.
    
    Args:
        bucket: S3 bucket name
        key: Object key (default: customer_behavior.csv)
        
    Returns:
        Dictionary mapping customer_id to CustomerBehavior
    """
    customers: dict[str, CustomerBehavior] = {}
    
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            # Parse comma-separated lists
            usual_countries = [c.strip() for c in row["usual_countries"].split(",")] if row["usual_countries"] else []
            usual_devices = [d.strip() for d in row["usual_devices"].split(",")] if row["usual_devices"] else []
            
            customer = CustomerBehavior(
                customer_id=row["customer_id"],
                usual_amount_avg=float(row["usual_amount_avg"]),
                usual_hours=row["usual_hours"],
                usual_countries=usual_countries,
                usual_devices=usual_devices,
            )
            customers[customer.customer_id] = customer
        
        logger.info(f"Loaded {len(customers)} customer profiles from s3://{bucket}/{key}")
        return customers
    
    except Exception as e:
        raise DataLoadError(f"s3://{bucket}/{key}", str(e))


def load_policies_from_s3(bucket: str, key: str = "fraud_policies.json") -> list[FraudPolicy]:
    """
    Load fraud policies from S3 bucket.
    
    Args:
        bucket: S3 bucket name
        key: Object key (default: fraud_policies.json)
        
    Returns:
        List of FraudPolicy objects
    """
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)
        
        policies = [FraudPolicy(**policy) for policy in data]
        logger.info(f"Loaded {len(policies)} fraud policies from s3://{bucket}/{key}")
        return policies
    
    except Exception as e:
        raise DataLoadError(f"s3://{bucket}/{key}", str(e))
