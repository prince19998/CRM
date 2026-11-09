from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import schemas
from .models import Lead

MYSQL_DUPLICATE_KEY = 1062


class LeadNotFoundError(LookupError):
    pass


class DuplicateEmailError(ValueError):
    pass


def _is_duplicate(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    return bool(orig is not None and orig.args and orig.args[0] == MYSQL_DUPLICATE_KEY)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_lead(db: Session, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise LeadNotFoundError(f"Lead {lead_id} was not found.")
    return lead


def list_leads(db: Session, limit: Optional[int] = None) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc())
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def search_leads(
    db: Session,
    search: Optional[str] = None,
    status: Optional[str] = None,
    lead_source: Optional[str] = None,
) -> list[Lead]:
    stmt = select(Lead)
    if search and search.strip():
        term = search.strip()

        stmt = stmt.where(
            or_(
                Lead.name.icontains(term, autoescape=True),
                Lead.email.icontains(term, autoescape=True),
                Lead.company.icontains(term, autoescape=True),
            )
        )
    if status:
        stmt = stmt.where(Lead.status == status)
    if lead_source:
        stmt = stmt.where(Lead.lead_source == lead_source)
    return list(db.scalars(stmt.order_by(Lead.created_at.desc(), Lead.id.desc())))


def _email_taken(db: Session, email: str, exclude_id: Optional[int] = None) -> bool:
    stmt = select(Lead.id).where(func.lower(Lead.email) == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(Lead.id != exclude_id)
    return db.scalars(stmt.limit(1)).first() is not None


def create_lead(db: Session, payload: schemas.LeadCreate) -> Lead:
    if _email_taken(db, payload.email):
        raise DuplicateEmailError("A lead with this email already exists.")
    lead = Lead(**payload.model_dump())
    db.add(lead)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate(exc):
            raise DuplicateEmailError("A lead with this email already exists.") from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(lead)
    return lead


def update_lead(db: Session, lead_id: int, payload: schemas.LeadUpdate) -> Lead:
    lead = get_lead(db, lead_id)
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes and _email_taken(db, changes["email"], exclude_id=lead_id):
        raise DuplicateEmailError("Another lead already uses this email.")
    for key, value in changes.items():
        setattr(lead, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate(exc):
            raise DuplicateEmailError("Another lead already uses this email.") from None
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead_id: int) -> None:
    lead = get_lead(db, lead_id) 
    db.delete(lead)
    _commit(db)


def get_stats(db: Session) -> dict:
    """Dashboard numbers, computed in MySQL with GROUP BY aggregates."""
    status_rows = db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    ).all()
    source_rows = db.execute(
        select(Lead.lead_source, func.count(Lead.id))
        .group_by(Lead.lead_source)
        .order_by(func.count(Lead.id).desc(), Lead.lead_source)
    ).all()
    status_counts = {status: 0 for status in schemas.LEAD_STATUSES}
    status_counts.update({status: int(count) for status, count in status_rows})
    total = sum(status_counts.values())
    converted = status_counts.get("Converted", 0)
    return {
        "total_leads": total,
        "status_counts": status_counts,
        "source_counts": {source: int(count) for source, count in source_rows},
        "conversion_rate": round((converted / total) * 100, 2) if total else 0.0,
    }
