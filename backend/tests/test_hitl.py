"""Tests for HITL functionality."""
import pytest
from datetime import datetime, timezone
from app.storage.local_json import LocalJSONHitlRepository
from app.api.schemas import HitlCase
import tempfile
import os


class TestHitlRepository:
    """Tests for HITL case management."""
    
    @pytest.fixture
    def repo(self):
        """Create a temporary HITL repository."""
        tmpdir = tempfile.mkdtemp()
        yield LocalJSONHitlRepository(tmpdir)
        # Cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_create_and_get_case(self, repo):
        """Test creating and retrieving a case."""
        case = HitlCase(
            case_id="HITL-001",
            transaction_id="T-001",
            status="OPEN",
            reason="borderline_confidence",
            created_at=datetime.now(timezone.utc).isoformat(),
            resolved_at=None,
            resolution=None,
        )
        
        repo.create_case(case)
        retrieved = repo.get_case("HITL-001")
        
        assert retrieved is not None
        assert retrieved.case_id == "HITL-001"
        assert retrieved.status == "OPEN"
    
    def test_list_open_cases(self, repo):
        """Test listing open cases."""
        # Create multiple cases
        for i in range(3):
            case = HitlCase(
                case_id=f"HITL-{i:03d}",
                transaction_id=f"T-{i:03d}",
                status="OPEN" if i < 2 else "RESOLVED",
                reason="test",
                created_at=datetime.now(timezone.utc).isoformat(),
                resolved_at=None,
                resolution=None,
            )
            repo.create_case(case)
        
        open_cases = repo.list_open_cases()
        
        assert len(open_cases) == 2
    
    def test_resolve_case(self, repo):
        """Test resolving a case."""
        case = HitlCase(
            case_id="HITL-001",
            transaction_id="T-001",
            status="OPEN",
            reason="policy_or_low_confidence",
            created_at=datetime.now(timezone.utc).isoformat(),
            resolved_at=None,
            resolution=None,
        )
        repo.create_case(case)
        
        resolved_at = datetime.now(timezone.utc).isoformat()
        repo.resolve_case(
            case_id="HITL-001",
            resolution={"decision": "APPROVE", "notes": "Manual review passed"},
            resolved_at=resolved_at,
        )
        
        resolved = repo.get_case("HITL-001")
        
        assert resolved.status == "RESOLVED"
        assert resolved.resolution["decision"] == "APPROVE"
        assert resolved.resolved_at == resolved_at
    
    def test_get_case_by_transaction(self, repo):
        """Test finding case by transaction ID."""
        case = HitlCase(
            case_id="HITL-001",
            transaction_id="T-SPECIFIC",
            status="OPEN",
            reason="test",
            created_at=datetime.now(timezone.utc).isoformat(),
            resolved_at=None,
            resolution=None,
        )
        repo.create_case(case)
        
        found = repo.get_case_by_transaction("T-SPECIFIC")
        
        assert found is not None
        assert found.transaction_id == "T-SPECIFIC"
    
    def test_get_nonexistent_case(self, repo):
        """Test getting a case that doesn't exist."""
        result = repo.get_case("NONEXISTENT")
        assert result is None
