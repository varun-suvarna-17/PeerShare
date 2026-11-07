"""Unit tests for sequence number handling, modular arithmetic, and window logic."""

import pytest

from app.protocol.constants import (
    SEQ_NUM_16BIT_MAX,
    SEQ_NUM_16BIT_MODULO,
    STOP_AND_WAIT_MODULO,
)
from app.protocol.sequence import (
    is_sequence_in_window,
    next_sequence_number,
    next_stop_and_wait_seq,
    sequence_distance,
    sequence_from_index,
    stop_and_wait_seq_from_index,
    validate_sr_window_sizes,
)


def test_next_sequence_number_linear() -> None:
    """Sequential increments within bounds."""
    assert next_sequence_number(0) == 1
    assert next_sequence_number(100) == 101
    assert next_sequence_number(65534) == 65535


def test_next_sequence_number_wraparound() -> None:
    """16-bit sequence number must wrap from 65535 to 0."""
    assert next_sequence_number(SEQ_NUM_16BIT_MAX) == 0


def test_sequence_from_index_16bit() -> None:
    """Mapping from monotonically increasing frame index to 16-bit sequence number."""
    assert sequence_from_index(0) == 0
    assert sequence_from_index(1) == 1
    assert sequence_from_index(65535) == 65535
    assert sequence_from_index(65536) == 0
    assert sequence_from_index(65537) == 1
    assert sequence_from_index(131072) == 0


def test_sequence_from_index_negative_raises() -> None:
    """Negative frame index must raise ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        sequence_from_index(-1)


def test_stop_and_wait_sequence_alternation() -> None:
    """Stop-and-Wait sequence numbers must alternate between 0 and 1."""
    assert next_stop_and_wait_seq(0) == 1
    assert next_stop_and_wait_seq(1) == 0


def test_stop_and_wait_seq_from_index() -> None:
    """Stop-and-Wait sequence number from monotonic index."""
    assert stop_and_wait_seq_from_index(0) == 0
    assert stop_and_wait_seq_from_index(1) == 1
    assert stop_and_wait_seq_from_index(2) == 0
    assert stop_and_wait_seq_from_index(3) == 1
    assert stop_and_wait_seq_from_index(100) == 0
    assert stop_and_wait_seq_from_index(101) == 1


def test_sequence_distance() -> None:
    """Verify circular forward distance computation."""
    assert sequence_distance(0, 0) == 0
    assert sequence_distance(10, 15) == 5
    assert sequence_distance(65530, 2) == 8
    assert sequence_distance(65535, 0) == 1
    assert sequence_distance(0, 65535) == 65535


def test_is_sequence_in_window_standard() -> None:
    """Sliding window check without wraparound."""
    base = 10
    window_size = 4
    # Expected window: [10, 11, 12, 13]
    for seq in [10, 11, 12, 13]:
        assert is_sequence_in_window(seq, base, window_size) is True

    # Out of window
    for seq in [8, 9, 14, 15, 20]:
        assert is_sequence_in_window(seq, base, window_size) is False


def test_is_sequence_in_window_wraparound() -> None:
    """Sliding window check across 16-bit wraparound boundary."""
    base = 65534
    window_size = 4
    # Expected window: [65534, 65535, 0, 1]
    for seq in [65534, 65535, 0, 1]:
        assert is_sequence_in_window(seq, base, window_size) is True

    # Out of window
    for seq in [65532, 65533, 2, 3]:
        assert is_sequence_in_window(seq, base, window_size) is False


def test_is_sequence_in_window_edge_cases() -> None:
    """Check window size edge cases (0, full space)."""
    assert is_sequence_in_window(10, 10, 0) is False
    assert is_sequence_in_window(10, 10, SEQ_NUM_16BIT_MODULO) is True
    assert is_sequence_in_window(500, 10, SEQ_NUM_16BIT_MODULO) is True


def test_is_sequence_in_window_stop_and_wait() -> None:
    """Window checking with Stop-and-Wait modulo 2."""
    assert is_sequence_in_window(0, 0, 1, modulo=STOP_AND_WAIT_MODULO) is True
    assert is_sequence_in_window(1, 0, 1, modulo=STOP_AND_WAIT_MODULO) is False
    assert is_sequence_in_window(1, 1, 1, modulo=STOP_AND_WAIT_MODULO) is True
    assert is_sequence_in_window(0, 1, 1, modulo=STOP_AND_WAIT_MODULO) is False


def test_validate_sr_window_sizes() -> None:
    """Selective Repeat constraint: sender_window + receiver_window <= sequence_space."""
    assert validate_sr_window_sizes(4, 4) is True
    assert validate_sr_window_sizes(32768, 32768) is True
    assert validate_sr_window_sizes(32769, 32768) is False
    assert validate_sr_window_sizes(0, 4) is False
    assert validate_sr_window_sizes(4, -1) is False

