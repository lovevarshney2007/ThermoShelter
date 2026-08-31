"""Shared utility helpers for the ThermoShelter backend."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def model_to_dict(model_instance) -> dict:
    """
    Convert a SQLAlchemy model instance to a plain dict.
    Only returns column attributes (not relationships).
    """
    return {
        col.name: getattr(model_instance, col.name)
        for col in model_instance.__table__.columns
    }
