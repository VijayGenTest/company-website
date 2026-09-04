"""Pydantic request/response schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
import re
import html


class ContactFormRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: str
    message: str
    captcha_token: str
    ip_address: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = html.escape(v.strip())
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Full name must be 2-100 characters.")
        if not re.match(r"^[a-zA-Z\s'\-]+$", v):
            raise ValueError("Full name contains invalid characters.")
        return v

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        v = html.escape(v.strip())
        if len(v) < 3 or len(v) > 200:
            raise ValueError("Subject must be 3-200 characters.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = html.escape(v.strip())
        if len(v) < 10 or len(v) > 2000:
            raise ValueError("Message must be 10-2000 characters.")
        return v


class ProcessResponse(BaseModel):
    success: bool
    submission_id: int
