"""Tests for data loading and normalization."""
import pytest
import tempfile
import os
import json
import csv
from pathlib import Path

from app.data.loader import (
    load_transactions,
    load_customer_behavior,
    load_policies,
    parse_hours,
    consolidate,
)
from app.api.schemas import Transaction, CustomerBehavior, FraudPolicy
from app.core.errors import TransactionNotFoundError, CustomerNotFoundError


class TestParseHours:
    """Test hour parsing functionality."""
    
    def test_parse_standard_hours(self):
        assert parse_hours("08-20") == (8, 20)
    
    def test_parse_early_hours(self):
        assert parse_hours("00-06") == (0, 6)
    
    def test_parse_late_hours(self):
        assert parse_hours("18-23") == (18, 23)
    
    def test_parse_invalid_returns_default(self):
        assert parse_hours("invalid") == (8, 20)
        assert parse_hours("") == (8, 20)


class TestLoadTransactions:
    """Test transaction loading."""
    
    def test_load_transactions_from_csv(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=[
                'transaction_id', 'customer_id', 'amount', 'currency',
                'country', 'channel', 'device_id', 'timestamp', 'merchant_id'
            ])
            writer.writeheader()
            writer.writerow({
                'transaction_id': 'T-001',
                'customer_id': 'CU-001',
                'amount': '1500.00',
                'currency': 'PEN',
                'country': 'PE',
                'channel': 'web',
                'device_id': 'D-01',
                'timestamp': '2025-12-17T10:15:00',
                'merchant_id': 'M-001',
            })
            f.flush()
            
            try:
                transactions = load_transactions(f.name)
                
                assert len(transactions) == 1
                assert 'T-001' in transactions
                assert transactions['T-001'].amount == 1500.00
                assert transactions['T-001'].currency == 'PEN'
            finally:
                os.unlink(f.name)


class TestLoadCustomerBehavior:
    """Test customer behavior loading with normalization."""
    
    def test_load_normalizes_countries_string(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=[
                'customer_id', 'usual_amount_avg', 'usual_hours',
                'usual_countries', 'usual_devices'
            ])
            writer.writeheader()
            writer.writerow({
                'customer_id': 'CU-001',
                'usual_amount_avg': '500.00',
                'usual_hours': '08-20',
                'usual_countries': 'PE',  # Single string
                'usual_devices': 'D-01',  # Single string
            })
            f.flush()
            
            try:
                customers = load_customer_behavior(f.name)
                
                assert len(customers) == 1
                assert customers['CU-001'].usual_countries == ['PE']
                assert customers['CU-001'].usual_devices == ['D-01']
            finally:
                os.unlink(f.name)
    
    def test_load_normalizes_comma_separated(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=[
                'customer_id', 'usual_amount_avg', 'usual_hours',
                'usual_countries', 'usual_devices'
            ])
            writer.writeheader()
            writer.writerow({
                'customer_id': 'CU-002',
                'usual_amount_avg': '1200.00',
                'usual_hours': '09-22',
                'usual_countries': 'PE, CL, CO',  # Comma-separated
                'usual_devices': 'D-01, D-02',
            })
            f.flush()
            
            try:
                customers = load_customer_behavior(f.name)
                
                assert customers['CU-002'].usual_countries == ['PE', 'CL', 'CO']
                assert customers['CU-002'].usual_devices == ['D-01', 'D-02']
            finally:
                os.unlink(f.name)


class TestLoadPolicies:
    """Test policy loading."""
    
    def test_load_policies_from_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            policies_data = [
                {
                    "policy_id": "FP-01",
                    "rule": "Monto > 3x promedio → CHALLENGE",
                    "version": "2025.1"
                }
            ]
            json.dump(policies_data, f)
            f.flush()
            
            try:
                policies = load_policies(f.name)
                
                assert len(policies) == 1
                assert policies[0].policy_id == "FP-01"
                assert "CHALLENGE" in policies[0].rule
            finally:
                os.unlink(f.name)


class TestConsolidate:
    """Test data consolidation."""
    
    def test_consolidate_merges_data(self):
        transactions = {
            'T-001': Transaction(
                transaction_id='T-001',
                customer_id='CU-001',
                amount=1500.0,
                currency='PEN',
                country='PE',
                channel='web',
                device_id='D-01',
                timestamp='2025-12-17T10:15:00',
                merchant_id='M-001',
            )
        }
        customers = {
            'CU-001': CustomerBehavior(
                customer_id='CU-001',
                usual_amount_avg=500.0,
                usual_hours='08-20',
                usual_countries=['PE'],
                usual_devices=['D-01'],
            )
        }
        
        consolidated = consolidate('T-001', transactions, customers)
        
        assert consolidated.transaction_id == 'T-001'
        assert consolidated.amount == 1500.0
        assert consolidated.usual_amount_avg == 500.0
        assert consolidated.usual_hours_start == 8
        assert consolidated.usual_hours_end == 20
    
    def test_consolidate_raises_on_missing_transaction(self):
        with pytest.raises(TransactionNotFoundError):
            consolidate('T-MISSING', {}, {})
    
    def test_consolidate_raises_on_missing_customer(self):
        transactions = {
            'T-001': Transaction(
                transaction_id='T-001',
                customer_id='CU-MISSING',
                amount=1500.0,
                currency='PEN',
                country='PE',
                channel='web',
                device_id='D-01',
                timestamp='2025-12-17T10:15:00',
                merchant_id='M-001',
            )
        }
        
        with pytest.raises(CustomerNotFoundError):
            consolidate('T-001', transactions, {})
