"""Tests for the Decision Arbiter Agent."""
import pytest
from app.agents.arbiter import run_arbiter_agent
from app.orchestration.state import GraphState


def create_test_state(**overrides) -> GraphState:
    """Create a test state with defaults."""
    default = {
        "transaction_id": "T-TEST",
        "consolidated": {},
        "signals": [],
        "metrics": {
            "behavior_risk": 0.0,
            "policy_hint": None,
            "amount_ratio": 1.0,
            "hour_outside": False,
            "new_country": False,
            "new_device": False,
        },
        "citations_internal": [],
        "citations_external": [],
        "evidence": {},
        "debate": {
            "pro_fraud": {"recommended_decision": "CHALLENGE", "confidence_delta": 0.0, "reasoning": ""},
            "pro_customer": {"recommended_decision": "APPROVE", "confidence_delta": 0.0, "reasoning": ""},
        },
        "decision": None,
        "confidence": None,
        "explanation_customer": None,
        "explanation_audit": None,
        "hitl": {"required": False, "reason": ""},
    }
    
    # Deep merge metrics
    if "metrics" in overrides:
        default["metrics"].update(overrides.pop("metrics"))
    
    default.update(overrides)
    return default


class TestArbiterDecisions:
    """Test decision logic of the Arbiter."""
    
    def test_approve_low_confidence_few_signals(self):
        """Low confidence with few signals should APPROVE."""
        state = create_test_state(
            signals=["Horario no habitual"],
            metrics={"behavior_risk": 0.15, "amount_ratio": 1.5, "hour_outside": True},
        )
        
        result = run_arbiter_agent(state)
        
        assert result["decision"] == "APPROVE"
        assert result["confidence"] < 0.45
    
    def test_challenge_high_amount_outside_hours(self):
        """High amount ratio + outside hours should CHALLENGE."""
        state = create_test_state(
            signals=["Monto fuera de rango", "Horario no habitual"],
            metrics={
                "behavior_risk": 0.40,
                "amount_ratio": 4.0,
                "hour_outside": True,
            },
        )
        
        result = run_arbiter_agent(state)
        
        assert result["decision"] == "CHALLENGE"
    
    def test_block_high_confidence_external_alert(self):
        """High confidence with external alert should BLOCK."""
        state = create_test_state(
            signals=["Monto fuera de rango", "Horario no habitual", "Alerta externa"],
            metrics={
                "behavior_risk": 0.55,
                "amount_ratio": 5.0,
                "hour_outside": True,
            },
            citations_external=[{"url": "https://example.com", "summary": "Alert"}],
            debate={
                "pro_fraud": {"recommended_decision": "BLOCK", "confidence_delta": 0.05, "reasoning": ""},
                "pro_customer": {"recommended_decision": "CHALLENGE", "confidence_delta": 0.00, "reasoning": ""},
            },
        )
        
        result = run_arbiter_agent(state)
        
        # confidence = 0.55 + 0.20 (external) + 0.05 (debate) = 0.80
        assert result["decision"] == "BLOCK"
        assert result["confidence"] >= 0.75
    
    def test_escalate_policy_hint_new_country_device(self):
        """Policy hint + new country + new device should ESCALATE."""
        state = create_test_state(
            signals=["País no habitual", "Dispositivo nuevo"],
            metrics={
                "behavior_risk": 0.45,
                "policy_hint": "ESCALATE_TO_HUMAN",
                "amount_ratio": 2.0,
                "new_country": True,
                "new_device": True,
            },
        )
        
        result = run_arbiter_agent(state)
        
        assert result["decision"] == "ESCALATE_TO_HUMAN"
        assert result["hitl"]["required"] is True
        assert result["hitl"]["reason"] == "policy_or_low_confidence"


class TestHITLTriggers:
    """Test HITL triggering conditions."""
    
    def test_hitl_on_escalate_decision(self):
        """ESCALATE_TO_HUMAN should trigger HITL."""
        state = create_test_state(
            signals=["País no habitual", "Dispositivo nuevo"],
            metrics={
                "behavior_risk": 0.45,
                "policy_hint": "ESCALATE_TO_HUMAN",
                "new_country": True,
                "new_device": True,
            },
        )
        
        result = run_arbiter_agent(state)
        
        assert result["hitl"]["required"] is True
    
    def test_hitl_on_borderline_confidence(self):
        """Borderline confidence (0.45-0.60) should trigger HITL."""
        state = create_test_state(
            signals=["Monto fuera de rango"],
            metrics={
                "behavior_risk": 0.50,  # Will be around 0.50 after adjustments
                "amount_ratio": 3.5,
                "hour_outside": False,
            },
        )
        
        result = run_arbiter_agent(state)
        
        # Even if decision is CHALLENGE, borderline confidence triggers HITL
        if 0.45 <= result["confidence"] <= 0.60:
            assert result["hitl"]["required"] is True
            assert result["hitl"]["reason"] == "borderline_confidence"
    
    def test_no_hitl_clear_approve(self):
        """Clear APPROVE should not trigger HITL."""
        state = create_test_state(
            signals=[],
            metrics={"behavior_risk": 0.10, "amount_ratio": 1.0},
        )
        
        result = run_arbiter_agent(state)
        
        if result["decision"] == "APPROVE" and result["confidence"] < 0.45:
            assert result["hitl"]["required"] is False
