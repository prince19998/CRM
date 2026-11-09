from sqlalchemy import Column, DateTime, Index, Integer, String, Text, func

from .database import Base


class Lead(Base):
    """Maps to the `leads` table created by database/schema.sql."""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    company = Column(String(200), nullable=False, default="")
    lead_source = Column(String(100), nullable=False, default="Website")
    status = Column(String(50), nullable=False, default="New")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_leads_status", "status"),
        Index("idx_leads_lead_source", "lead_source"),
        Index("idx_leads_name", "name"),
        Index("idx_leads_company", "company"),
        Index("idx_leads_created_at", "created_at"),
    )

