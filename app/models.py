from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class ItemLink(Base):
    __tablename__ = 'item_links'
    __table_args__ = (UniqueConstraint('rally_object_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rally_object_id: Mapped[str] = mapped_column(String(64), index=True)
    rally_formatted_id: Mapped[str] = mapped_column(String(64), index=True)
    rally_type: Mapped[str] = mapped_column(String(64))
    rally_parent_object_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    gitlab_project_id: Mapped[str] = mapped_column(String(128))
    gitlab_iid: Mapped[int] = mapped_column(Integer, index=True)
    gitlab_type: Mapped[str] = mapped_column(String(32), default='issue')
    last_rally_updated: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_gitlab_updated: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(32), default='linked')
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

class SyncLog(Base):
    __tablename__ = 'sync_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    operation: Mapped[str] = mapped_column(String(64))
    scope: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text, default='')
