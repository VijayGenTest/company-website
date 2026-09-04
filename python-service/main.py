"""
Python FastAPI service - Contact Form Processor
Handles: input sanitisation, CAPTCHA verification, email, database logging.
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from schemas import ContactFormRequest, ProcessResponse
from services.captcha import verify_captcha
from services.email_service import send_email_notification
from services.database import log_submission, log_spam_attempt, init_db, _pg_pool

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# CQ FIX [CQ-003]: Replaced deprecated @app.on_event("startup") with the
# recommended lifespan context manager pattern (FastAPI 0.93+).
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    init_db()
    logger.info("Python service started.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    global _pg_pool
    if _pg_pool:
        _pg_pool.closeall()
        logger.info("PostgreSQL connection pool closed.")


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Company Website - Form Processor",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://node-backend:3000", "http://localhost:3000"],
    allow_methods=["POST", "GET"],
    # SECURITY FIX [SEC-006]: Restrict allowed headers to only those the
    # service actually needs, rather than the wildcard '*'.
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


async def _send_email_background(submission_id: int, payload: ContactFormRequest) -> None:
    """
    Background task: send email notification after the response has been returned.
    PERF FIX [PERF-003]: Email is sent asynchronously so the API response is
    not held up by SMTP / SendGrid latency (up to 30s with retries).
    """
    email_sent = send_email_notification(
        name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
    )
    logger.info("Background email task complete for submission %d. Sent: %s", submission_id, email_sent)


@app.post("/process", response_model=ProcessResponse)
@limiter.limit("20/minute")
async def process_contact_form(
    request: Request,
    payload: ContactFormRequest,
    background_tasks: BackgroundTasks,
):
    """
    Process a contact form submission.
    Steps: 1) CAPTCHA verify, 2) Log to DB (email_sent=False),
           3) Enqueue email as background task, 4) Return response immediately.
    """
    ip = payload.ip_address or "unknown"
    logger.info("Processing submission from IP: %s", ip)

    # Step 1: CAPTCHA verification (async, non-blocking)
    captcha_ok, captcha_score = await verify_captcha(payload.captcha_token, ip)
    if not captcha_ok:
        log_spam_attempt(ip, captcha_passed=False)
        raise HTTPException(status_code=422, detail="CAPTCHA verification failed.")

    # Step 2: Log to database immediately (email_sent=False initially)
    submission_id = log_submission(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
        ip_address=ip,
        captcha_passed=True,
        captcha_score=captcha_score,
        email_sent=False,
    )

    # Step 3: Enqueue email send as a background task (non-blocking)
    # PERF FIX [PERF-003]: Response is returned to client immediately;
    # email delivery happens after the response is sent.
    background_tasks.add_task(_send_email_background, submission_id, payload)

    logger.info("Submission %d logged. Email enqueued as background task.", submission_id)
    return ProcessResponse(success=True, submission_id=submission_id)
