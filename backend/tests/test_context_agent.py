"""Tests for the Transaction Context Agent."""
import pytest
from app.agents.transaction_context import run_transaction_context_agent, extract_hour
from app.orchestration.state import create_initial_state


class TestExtractHour:
    """Tests for hour extraction from timestamps."""
    
    def test_extract_hour_standard(self):
        assert extract_hour("2025-12-17T10:15:00") == 10
    
    def test_extract_hour_midnight(self):
        assert extract_hour("2025-12-17T00:30:00") == 0
    
    def test_extract_hour_late_night(self):
        assert extract_hour("2025-12-17T23:45:00") == 23
    
    def test_extract_hour_with_timezone(self):
        assert extract_hour("2025-12-17T10:15:00Z") == 10


class TestTransactionContextAgent:
    """Tests for the Transaction Context Agent."""
    
    def get_consolidated_data(self, **overrides):
        """Create test consolidated data."""
        data = {
            "transaction_id": "T-TEST",
            "customer_id": "CU-TEST",
            "amount": 500.0,
            "currency": "PEN",
            "country": "PE",
            "channel": "web",
            "device_id": "D-01",
            "timestamp": "2025-12-17T10:15:00",
            "merchant_id": "M-001",
            "usual_amount_avg": 500.0,
            "usual_hours_start": 8,
            "usual_hours_end": 20,
            "usual_countries": ["PE"],
            "usual_devices": ["D-01"],
        }
        data.update(overrides)
        return data
    
    def test_normal_transaction_no_signals(self):
        """Normal transaction should produce no signals."""
        consolidated = self.get_consolidated_data()
        state = create_initial_state("T-TEST", consolidated)
        
        result = run_transaction_context_agent(state)
        
        assert len(result["signals"]) == 0
        assert result["metrics"]["amount_ratio"] == 1.0
        assert result["metrics"]["hour_outside"] is False
        assert result["metrics"]["new_country"] is False
        assert result["metrics"]["new_device"] is False
    
    def test_high_amount_signal(self):
        """Amount > 3x average should trigger signal."""
        consolidated = self.get_consolidated_data(amount=2000.0)  # 4x average
        state = create_initial_state("T-TEST", consolidated)
        
        result = run_transaction_context_agent(state)
        
        assert "Monto fuera de rango" in result["signals"]
        assert result["metrics"]["amount_ratio"] == 4.0
    
    def test_outside_hours_signal(self):
        """Transaction outside usual hours should trigger signal."""
        consolidated = self.get_consolidated_data(timestamp="2025-12-17T03:15:00")
        state = create_initial_state("T-TEST", consolidated)
        
        result = run_transaction_context_agent(state)
        
        assert "Horario no habitual" in result["signals"]
        assert result["metrics"]["hour_outside"] is True
    
    def test_new_country_signal(self):
        """Transaction from new country should trigger signal."""
        consolidated = self.get_consolidated_data(country="CL")
        state = create_initial_state("T-TEST", consolidated)
        
        result = run_transaction_context_agent(state)
        
        assert "País no habitual" in result["signals"]
        assert result["metrics"]["new_country"] is True
    
    def test_new_device_signal(self):
        """Transaction from new device should trigger signal."""
        consolidated = self.get_consolidated_data(device_id="D-99")
        state = create_initial_state("T-TEST", consolidated)
        
        result = run_transaction_context_agent(state)
        
        assert "Dispositivo nuevo" in result["signals"]
        assert result["metrics"]["new_device"] is True
    
    def test_multiple_signals(self):
        """Multiple issues should produce multiple signals."""
        consolidated = self.get_consolidated_data(
            amount=2500.0,  # 5x average
            timestamp="2025-12-17T03:15:00",  # Outside hours
            country="CL",  # New country
            device_id="D-99",  # New device
        )
        state = create_initial_state("T-TEST", consolidated)
        
        result = run_transaction_context_agent(state)
        
        assert len(result["signals"]) == 4
        assert "Monto fuera de rango" in result["signals"]
        assert "Horario no habitual" in result["signals"]
        assert "País no habitual" in result["signals"]
        assert "Dispositivo nuevo" in result["signals"]
    
    def test_zero_average_amount(self):
        """Zero average should handle gracefully."""
        consolidated = self.get_consolidated_data(
            amount=100.0,
            usual_amount_avg=0.0
        )
        state = create_initial_state("T-TEST", consolidated)
        
        result = run_transaction_context_agent(state)
        
        assert result["metrics"]["amount_ratio"] == 999.0
        assert "Monto fuera de rango" in result["signals"]
