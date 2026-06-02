# AnoChat Workspace

Standalone FastAPI/PostgreSQL migration of the previous Workspace module.

## Stack

- FastAPI with Swagger/OpenAPI at `/docs`
- PostgreSQL with SQLAlchemy models
- Alembic migrations
- JWT authentication and bcrypt password hashing
- WebSocket chat endpoint at `/ws/chatters/{chatter_id}`
- Local upload storage in `uploads/`
- Static frontend at `/frontend/index.html`

## Setup

```powershell
cd "custom_messenger_odoo 3/backend"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Start PostgreSQL locally or use Docker from the project root:

```powershell
cd "custom_messenger_odoo 3"
docker compose up --build
```

Run migrations:

```powershell
cd "custom_messenger_odoo 3/backend"
alembic upgrade head
```

Run the API without Docker:

```powershell
cd "custom_messenger_odoo 3"
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- API docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:8000/frontend/index.html`

## Test Credentials

- Admin: `admin@example.com` / `Admin123!`
- Customer: `customer@example.com` / `Customer123!`

The seed users are created on startup if they do not already exist.

## Important Routes

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/users`
- `GET/POST/PUT/DELETE /api/projects`
- `GET/POST/PUT/DELETE /api/chatters`
- `GET/POST /api/chatters/{id}/messages`
- `PUT/DELETE /api/messages/{id}`
- `POST /api/attachments/upload`
- `GET/DELETE /api/attachments/{id}`
- `GET /api/activity-logs`
- `GET /api/email-logs`
- `POST /api/email/inbound`
- `GET /api/monitoring/health`
- `GET /api/monitoring/stats`

## Migration Reports

- `FEATURE_MAPPING.md`
- `FINAL_MIGRATION_REPORT.md`
- `ODOO_REMOVAL_CHECKLIST.md`
