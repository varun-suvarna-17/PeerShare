"""Sequence number arithmetic and circular window utilities for ARQ protocols."""

from app.protocol.constants import (
    SEQ_NUM_16BIT_MODULO,
    STOP_AND_WAIT_MODULO,
)


def next_sequence_number(seq: int, modulo: int = SEQ_NUM_16BIT_MODULO) -> int:
    """Compute the next sequence number wrapping around modulo.

    Args:
        seq: Current sequence number.
        modulo: Size of the sequence number space (default 65536).

    Returns:
        Next sequence number.
    """
    return (seq + 1) % modulo


def sequence_from_index(frame_index: int, modulo: int = SEQ_NUM_16BIT_MODULO) -> int:
    """Map an absolute frame index to a circular wire sequence number.

    Args:
        frame_index: Absolute monotonic frame index (0, 1, 2, ...).
        modulo: Size of sequence space (default 65536 for 16-bit, 2 for Stop-and-Wait).

    Returns:
        Wire sequence number within [0, modulo - 1].
    """
    if frame_index < 0:
        raise ValueError(f"Frame index must be non-negative, got {frame_index}")
    return frame_index % modulo


def next_stop_and_wait_seq(current_seq: int) -> int:
    """Get the alternating 1-bit sequence number (0 -> 1 -> 0) for Stop-and-Wait.

    Args:
        current_seq: Current 1-bit sequence number (0 or 1).

    Returns:
        Alternated sequence number (1 if 0, 0 if 1).
    """
    return (current_seq + 1) % STOP_AND_WAIT_MODULO


def stop_and_wait_seq_from_index(frame_index: int) -> int:
    """Map an absolute frame index to a 1-bit Stop-and-Wait sequence number (0 or 1).

    Args:
        frame_index: Absolute monotonic frame index.

    Returns:
        0 or 1.
    """
    return sequence_from_index(frame_index, STOP_AND_WAIT_MODULO)


def sequence_distance(seq_from: int, seq_to: int, modulo: int = SEQ_NUM_16BIT_MODULO) -> int:
    """Compute the forward distance from seq_from to seq_to in circular sequence space.

    Args:
        seq_from: Starting sequence number.
        seq_to: Target sequence number.
        modulo: Size of sequence space.

    Returns:
        Number of steps forward from seq_from to seq_to (in [0, modulo - 1]).
    """
    return (seq_to - seq_from) % modulo


def is_sequence_in_window(
    seq: int,
    base: int,
    window_size: int,
    modulo: int = SEQ_NUM_16BIT_MODULO,
) -> bool:
    """Check whether a sequence number is within a circular sliding window [base, base + window_size).

    Args:
        seq: The sequence number to check.
        base: The base (oldest unacknowledged or next expected) sequence number.
        window_size: Size of the window.
        modulo: Size of sequence space.

    Returns:
        True if seq is inside the window, False otherwise.
    """
    if window_size <= 0:
        return False
    if window_size > modulo:
        return True
    return sequence_distance(base, seq, modulo) < window_size


def validate_sr_window_sizes(
    sender_window: int,
    receiver_window: int,
    modulo: int = SEQ_NUM_16BIT_MODULO,
) -> bool:
    """Validate that Selective Repeat window sizes satisfy the half-sequence-space constraint.

    According to ARQ theory and project documentation:
    sender_window + receiver_window <= modulo

    Args:
        sender_window: Sender sliding window size.
        receiver_window: Receiver sliding window size.
        modulo: Size of sequence space (default 65536).

    Returns:
        True if the window sizes are valid, False otherwise.
    """
    if sender_window <= 0 or receiver_window <= 0:
        return False
    return (sender_window + receiver_window) <= modulo

