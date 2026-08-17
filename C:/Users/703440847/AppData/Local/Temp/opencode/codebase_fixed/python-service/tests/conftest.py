"""
Pytest configuration for the Python FastAPI service tests.

CQ FIX [CQ-006]: Added anyio_backend fixture so @pytest.mark.anyio tests
actually run asynchronously. Without this, async tests can silently pass
without executing their async body.
"""
import pytest


@pytest.fixture
def anyio_backend():
    """Run anyio-based async tests on the asyncio backend."""
    return "asyncio"
