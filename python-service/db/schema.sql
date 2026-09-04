-- Company Website Database Schema (PostgreSQL 14+)

CREATE TABLE IF NOT EXISTS contact_submissions (
    submission_id   SERIAL PRIMARY KEY,
    full_name       VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    NOT NULL,
    phone           VARCHAR(20),
    subject         VARCHAR(200)    NOT NULL,
    message         TEXT            NOT NULL,
    submitted_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ip_address      VARCHAR(45)     NOT NULL,
    captcha_passed  BOOLEAN         NOT NULL DEFAULT FALSE,
    captcha_score   DECIMAL(3,2),
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS email_notifications (
    notification_id SERIAL PRIMARY KEY,
    submission_id   INTEGER         NOT NULL REFERENCES contact_submissions(submission_id),
    recipient_email VARCHAR(150)    NOT NULL,
    sent_at         TIMESTAMPTZ,
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS spam_log (
    log_id          SERIAL PRIMARY KEY,
    ip_address      VARCHAR(45)     NOT NULL,
    attempt_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    captcha_passed  BOOLEAN         NOT NULL,
    blocked         BOOLEAN         NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS page_visits (
    visit_id        SERIAL PRIMARY KEY,
    page_name       VARCHAR(100)    NOT NULL,
    visited_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    session_id      VARCHAR(64),
    user_agent      TEXT
);

CREATE INDEX IF NOT EXISTS idx_submissions_email     ON contact_submissions(email);
CREATE INDEX IF NOT EXISTS idx_submissions_submitted ON contact_submissions(submitted_at);
CREATE INDEX IF NOT EXISTS idx_spam_ip               ON spam_log(ip_address);
CREATE INDEX IF NOT EXISTS idx_notifications_sub     ON email_notifications(submission_id);
