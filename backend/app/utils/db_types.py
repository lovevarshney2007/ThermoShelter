from sqlalchemy.types import TypeDecorator, JSON
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

class JSONB(TypeDecorator):
    """
    Custom JSONB type that falls back to JSON for SQLite.
    Allows running tests with SQLite while using PostgreSQL in production.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_JSONB())
        else:
            return dialect.type_descriptor(JSON())
