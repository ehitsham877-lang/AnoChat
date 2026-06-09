from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.access_requests.routes import router as access_requests_router
from app.activity_logs.routes import router as activity_logs_router
from app.attachments.routes import router as attachments_router
from app.auth.password import hash_password
from app.auth.routes import router as auth_router
from app.chatters.routes import router as chatters_router
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.email_logs.routes import router as email_logs_router
from app.messages.routes import router as messages_router
from app.messages.websocket import router as websocket_router
from app.models import Role, User
from app.monitoring.routes import router as monitoring_router
from app.notifications.routes import router as notifications_router
from app.ops.routes import router as ops_router
from app.projects.routes import router as projects_router
from app.roles.permissions import KNOWN_ROLES
from app.users.routes import router as users_router

settings = get_settings()
frontend_root = Path(__file__).resolve().parents[2] / "frontend"
if not frontend_root.exists():
    frontend_root = Path("/frontend")

app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_data(db: Session) -> None:
    roles = {}
    for name in KNOWN_ROLES:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=f"{name.title()} role")
            db.add(role)
            db.flush()
        roles[name] = role

    def upsert_seed_user(name: str, email: str, password: str, role_name: str) -> None:
        email_key = str(email).strip().lower()
        user = db.query(User).filter((User.email == email_key) | (User.login == email_key)).first()
        if not user:
            user = User(name=name)
            db.add(user)
        user.name = name
        user.login = email_key
        user.email = email_key
        user.active = True
        user.hashed_password = hash_password(password)
        user.roles = [roles[role_name]]

    upsert_seed_user("Admin User", settings.seed_admin_email, settings.seed_admin_password, "admin")
    upsert_seed_user("Customer User", settings.seed_customer_email, settings.seed_customer_password, "customer")
    db.commit()


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    dialect = engine.dialect.name
    deleted_at_type = "TIMESTAMP WITH TIME ZONE" if dialect == "postgresql" else "DATETIME"
    deleted_default = "FALSE" if dialect == "postgresql" else "0"
    message_columns = {column["name"] for column in inspector.get_columns("messages")} if inspector.has_table("messages") else set()
    message_additions = {
        "original_body": "ALTER TABLE messages ADD COLUMN original_body TEXT",
        "is_deleted": f"ALTER TABLE messages ADD COLUMN is_deleted BOOLEAN DEFAULT {deleted_default}",
        "deleted_by_id": "ALTER TABLE messages ADD COLUMN deleted_by_id INTEGER",
        "deleted_at": f"ALTER TABLE messages ADD COLUMN deleted_at {deleted_at_type}",
        "reply_to_id": "ALTER TABLE messages ADD COLUMN reply_to_id INTEGER",
    }
    attachment_columns = {column["name"] for column in inspector.get_columns("attachments")} if inspector.has_table("attachments") else set()
    attachment_additions = {
        "is_deleted": f"ALTER TABLE attachments ADD COLUMN is_deleted BOOLEAN DEFAULT {deleted_default}",
        "deleted_by_id": "ALTER TABLE attachments ADD COLUMN deleted_by_id INTEGER",
        "deleted_at": f"ALTER TABLE attachments ADD COLUMN deleted_at {deleted_at_type}",
        "duration_seconds": "ALTER TABLE attachments ADD COLUMN duration_seconds FLOAT",
    }
    user_columns = {column["name"] for column in inspector.get_columns("users")} if inspector.has_table("users") else set()
    user_additions = {
        "active_session_version": "ALTER TABLE users ADD COLUMN active_session_version INTEGER DEFAULT 0 NOT NULL",
        "read_only": f"ALTER TABLE users ADD COLUMN read_only BOOLEAN DEFAULT {deleted_default} NOT NULL",
        "avatar_attachment_id": "ALTER TABLE users ADD COLUMN avatar_attachment_id INTEGER",
    }
    project_member_columns = {column["name"] for column in inspector.get_columns("project_members")} if inspector.has_table("project_members") else set()
    project_member_additions = {
        "is_read_only": f"ALTER TABLE project_members ADD COLUMN is_read_only BOOLEAN DEFAULT {deleted_default} NOT NULL",
    }
    chatter_member_columns = {column["name"] for column in inspector.get_columns("chatter_members")} if inspector.has_table("chatter_members") else set()
    chatter_member_additions = {
        "is_read_only": f"ALTER TABLE chatter_members ADD COLUMN is_read_only BOOLEAN DEFAULT {deleted_default} NOT NULL",
    }
    notification_preference_columns = {column["name"] for column in inspector.get_columns("notification_preferences")} if inspector.has_table("notification_preferences") else set()
    notification_preference_additions = {
        "email_alerts_enabled": f"ALTER TABLE notification_preferences ADD COLUMN email_alerts_enabled BOOLEAN DEFAULT {deleted_default} NOT NULL",
        "email_chatter_messages": f"ALTER TABLE notification_preferences ADD COLUMN email_chatter_messages BOOLEAN DEFAULT TRUE NOT NULL" if dialect == "postgresql" else "ALTER TABLE notification_preferences ADD COLUMN email_chatter_messages BOOLEAN DEFAULT 1 NOT NULL",
        "email_workspace_updates": f"ALTER TABLE notification_preferences ADD COLUMN email_workspace_updates BOOLEAN DEFAULT TRUE NOT NULL" if dialect == "postgresql" else "ALTER TABLE notification_preferences ADD COLUMN email_workspace_updates BOOLEAN DEFAULT 1 NOT NULL",
    }
    with engine.begin() as connection:
        for column, statement in user_additions.items():
            if column not in user_columns:
                connection.execute(text(statement))
        for column, statement in project_member_additions.items():
            if column not in project_member_columns:
                connection.execute(text(statement))
        for column, statement in chatter_member_additions.items():
            if column not in chatter_member_columns:
                connection.execute(text(statement))
        for column, statement in notification_preference_additions.items():
            if column not in notification_preference_columns:
                connection.execute(text(statement))
        for column, statement in message_additions.items():
            if column not in message_columns:
                connection.execute(text(statement))
        for column, statement in attachment_additions.items():
            if column not in attachment_columns:
                connection.execute(text(statement))


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    with SessionLocal() as db:
        seed_data(db)


app.include_router(auth_router)
app.include_router(access_requests_router)
app.include_router(users_router)
app.include_router(projects_router)
app.include_router(chatters_router)
app.include_router(messages_router)
app.include_router(attachments_router)
app.include_router(activity_logs_router)
app.include_router(email_logs_router)
app.include_router(monitoring_router)
app.include_router(notifications_router)
app.include_router(ops_router)
app.include_router(websocket_router)

if frontend_root.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_root), html=True), name="frontend")


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/docs", "frontend": "/frontend/index.html"}
