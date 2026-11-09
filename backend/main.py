import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import ai_service, crud, schemas
from .database import DatabaseUnavailableError, check_connection, get_db
from .models import Lead

logger = logging.getLogger("uvicorn.error")

AI_CONTEXT_LIMIT = 300


@asynccontextmanager
async def lifespan(app: FastAPI):

    try:
        check_connection()
        logger.info("MySQL connection OK.")
    except DatabaseUnavailableError as exc:

        logger.error("Database check failed: %s", exc)
    yield


app = FastAPI(
    title="AI-Powered CRM Lead Assistant",
    description="CRM lead management and AI assistance backed by MySQL.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):

    orig = getattr(exc, "orig", None)
    logger.error("Database error %s: %s", exc.__class__.__name__, orig or "")
    if isinstance(exc, OperationalError):
        detail = (
            "Cannot reach the MySQL database. Check that MySQL is running and that "
            "the DB_* values in .env are correct."
        )
    else:
        detail = f"Database error ({exc.__class__.__name__})."
    return JSONResponse(status_code=503, content={"detail": detail})


def lead_context(lead: Lead) -> dict:

    return {
        "id": lead.id,
        "name": lead.name,
        "company": lead.company,
        "lead_source": lead.lead_source,
        "status": lead.status,
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }


def _lead_or_404(db: Session, lead_id: int) -> Lead:
    try:
        return crud.get_lead(db, lead_id)
    except crud.LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _ai_call(func, *args):
    """Run an LLM call. Failures become a 503 and never affect CRUD endpoints."""
    try:
        return {"result": func(*args)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {exc}")


@app.get("/")
def root():
    return {"message": "AI-Powered CRM Lead Assistant API", "docs": "/docs"}


@app.get("/health")
def health():
    try:
        check_connection()
    except DatabaseUnavailableError as exc:
        return JSONResponse(status_code=503, content={"status": "error", "database": str(exc)})
    return {"status": "ok", "database": "connected"}



@app.post("/leads/", response_model=schemas.LeadResponse, status_code=201)
def create_lead(payload: schemas.LeadCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_lead(db, payload)
    except crud.DuplicateEmailError as exc:
        raise HTTPException(status_code=409, detail=str(exc))



@app.get("/leads/search/", response_model=list[schemas.LeadResponse])
def search_leads(
    search: Optional[str] = Query(default=None, max_length=160),
    status: Optional[str] = None,
    lead_source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if status and status not in schemas.LEAD_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid lead status.")
    return crud.search_leads(db, search, status, lead_source)


@app.get("/leads/", response_model=list[schemas.LeadResponse])
def list_leads(db: Session = Depends(get_db)):
    return crud.list_leads(db)


@app.get("/leads/{lead_id}", response_model=schemas.LeadResponse)
def read_lead(lead_id: int, db: Session = Depends(get_db)):
    return _lead_or_404(db, lead_id)


@app.put("/leads/{lead_id}", response_model=schemas.LeadResponse)
def update_lead(lead_id: int, payload: schemas.LeadUpdate, db: Session = Depends(get_db)):
    try:
        return crud.update_lead(db, lead_id, payload)
    except crud.LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except crud.DuplicateEmailError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.delete("/leads/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_lead(db, lead_id)
    except crud.LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": f"Lead {lead_id} deleted successfully."}



@app.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    return crud.get_stats(db)



@app.post("/ai/lead-summary/{lead_id}", response_model=schemas.AIResponse)
def generate_lead_summary(lead_id: int, db: Session = Depends(get_db)):
    context = lead_context(_lead_or_404(db, lead_id))
    return _ai_call(ai_service.lead_summary, context)


@app.post("/ai/follow-up/{lead_id}", response_model=schemas.AIResponse)
def generate_follow_up(lead_id: int, db: Session = Depends(get_db)):
    context = lead_context(_lead_or_404(db, lead_id))
    return _ai_call(ai_service.follow_up_suggestion, context)


def _ai_snapshot(db: Session) -> tuple[dict, list[dict]]:
    leads = crud.list_leads(db, limit=AI_CONTEXT_LIMIT)
    contexts = [lead_context(lead) for lead in leads]
    stats = crud.get_stats(db)

    stats["records_supplied_to_ai"] = len(contexts)
    return stats, contexts


@app.post("/ai/chat", response_model=schemas.AIResponse)
def chat_with_crm(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    stats, contexts = _ai_snapshot(db)
    return _ai_call(ai_service.crm_chat, payload.question, contexts, stats)


@app.get("/ai/insights", response_model=schemas.AIResponse)
def generate_insights(db: Session = Depends(get_db)):
    stats, contexts = _ai_snapshot(db)
    return _ai_call(ai_service.overall_insights, stats, contexts)
