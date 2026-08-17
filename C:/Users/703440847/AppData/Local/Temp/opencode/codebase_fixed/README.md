# Company Website with Contact Us Feature

## Stack
- **Frontend**: HTML5 / CSS3 / Vanilla JavaScript + Bootstrap 5
- **Backend (Node.js)**: Express.js — page routing, API gateway
- **Backend (Python)**: FastAPI — form processing, CAPTCHA, email, DB
- **Database**: PostgreSQL (SQLite for dev)
- **Email**: SendGrid (or SMTP fallback)
- **CAPTCHA**: Google reCAPTCHA v3

## Project Structure
```
company_website/
├── node-backend/       # Node.js Express backend
├── python-service/     # Python FastAPI form processor
├── frontend/           # HTML/CSS/JS pages
├── nginx/              # Nginx config
├── docker-compose.yml
└── .env.example
```

## Setup
1. Copy `.env.example` to `.env` and fill in your credentials
2. Run `docker-compose up --build`
3. Visit http://localhost
