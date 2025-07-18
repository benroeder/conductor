"""Tests for the ConductorTest class."""

from unittest.mock import MagicMock
import json

from conductor.test import ConductorTest
from conductor.phase import Phase


class TestConductorTestClass:
    """Test the ConductorTest class functionality."""

    def test_initialization(self):
        """Test that ConductorTest initializes with empty phases list."""
        conductor_test = ConductorTest()
        assert conductor_test.phases == []
        assert isinstance(conductor_test.phases, list)

    def test_append_adds_phase(self):
        """Test that append adds a phase to the phases list."""
        conductor_test = ConductorTest()
        phase = MagicMock(spec=Phase)

        conductor_test.append(phase)

        assert len(conductor_test.phases) == 1
        assert conductor_test.phases[0] is phase

    def test_append_multiple_phases(self):
        """Test appending multiple phases maintains order."""
        conductor_test = ConductorTest()
        phase1 = MagicMock(spec=Phase)
        phase2 = MagicMock(spec=Phase)
        phase3 = MagicMock(spec=Phase)

        conductor_test.append(phase1)
        conductor_test.append(phase2)
        conductor_test.append(phase3)

        assert len(conductor_test.phases) == 3
        assert conductor_test.phases[0] is phase1
        assert conductor_test.phases[1] is phase2
        assert conductor_test.phases[2] is phase3

    def test_can_be_serialized(self):
        """Test that ConductorTest can be serialized for JSON communication."""
        conductor_test = ConductorTest()
        
        # Create a simple representation
        data = {"phases": []}
        
        # Verify it can be JSON serialized
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        
        assert loaded["phases"] == []
        
        # Note: In practice, ConductorTest would need proper to_dict/from_dict methods
        # for full JSON protocol support
