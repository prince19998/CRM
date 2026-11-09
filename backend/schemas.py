from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

LEAD_STATUSES = ["New", "Contacted", "Interested", "Converted", "Lost"]
LEAD_SOURCES = ["Website", "LinkedIn", "Referral", "Email", "Phone", "Event", "Other"]


def _check_status(value: str) -> str:
    if value not in LEAD_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(LEAD_STATUSES)}")
    return value


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    company: str = Field(default="", max_length=200)
    lead_source: str = Field(default="Website", max_length=100)
    status: str = "New"
    notes: str = ""

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("company")
    @classmethod
    def clean_company(cls, value: str) -> str:
        return value.strip()

    @field_validator("lead_source")
    @classmethod
    def clean_source(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Lead source cannot be empty.")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        return _check_status(value)


class LeadUpdate(BaseModel):
    """Partial update: only fields that are sent are changed. Sending null is rejected."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    company: Optional[str] = Field(default=None, max_length=200)
    lead_source: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def no_explicit_nulls(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"'{field}' cannot be null.")
        return self

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value

    @field_validator("email")
    @classmethod
    def lower_email(cls, value):
        return value.strip().lower() if value is not None else value

    @field_validator("company")
    @classmethod
    def clean_company(cls, value):
        return value.strip() if value is not None else value

    @field_validator("lead_source")
    @classmethod
    def clean_source(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Lead source cannot be empty.")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        return value if value is None else _check_status(value)


class LeadResponse(BaseModel):
    """Plain response model (no input validators) so stored rows always serialise."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    company: str
    lead_source: str
    status: str
    notes: Optional[str] = ""
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


class AIResponse(BaseModel):
    result: str
