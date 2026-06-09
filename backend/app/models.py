from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

project_members = Table(
    "project_members",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("is_read_only", Boolean, default=False, nullable=False),
)

chatter_members = Table(
    "chatter_members",
    Base.metadata,
    Column("chatter_id", ForeignKey("chatters.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("is_admin", Boolean, default=False, nullable=False),
    Column("is_pinned", Boolean, default=False, nullable=False),
    Column("is_starred", Boolean, default=False, nullable=False),
    Column("is_archived", Boolean, default=False, nullable=False),
    Column("unread_count", Integer, default=0, nullable=False),
    Column("last_seen_at", DateTime(timezone=True)),
    Column("last_seen_message_id", Integer, default=0, nullable=False),
    Column("is_read_only", Boolean, default=False, nullable=False),
)

message_attachments = Table(
    "message_attachments",
    Base.metadata,
    Column("message_id", ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
    Column("attachment_id", ForeignKey("attachments.id", ondelete="CASCADE"), primary_key=True),
)

message_seen = Table(
    "message_seen",
    Base.metadata,
    Column("message_id", ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    login: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    read_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64))
    avatar_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id", ondelete="SET NULL"), nullable=True)
    messenger_status: Mapped[str] = mapped_column(String(32), default="offline")
    messenger_last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active_session_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")
    projects: Mapped[list["Project"]] = relationship(secondary=project_members, back_populates="members", lazy="selectin")
    chatters: Mapped[list["Chatter"]] = relationship(secondary=chatter_members, back_populates="members", lazy="selectin")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str | None] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="normal")
    stage: Mapped[str] = mapped_column(String(32), default="planning")
    start_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    manager: Mapped[User | None] = relationship(foreign_keys=[manager_id], lazy="selectin")
    customer: Mapped[User | None] = relationship(foreign_keys=[customer_id], lazy="selectin")
    members: Mapped[list[User]] = relationship(secondary=project_members, back_populates="projects", lazy="selectin")


class Chatter(TimestampMixin, Base):
    __tablename__ = "chatters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    conversation_type: Mapped[str] = mapped_column(String(32), default="group")
    channel_scope: Mapped[str] = mapped_column(String(32), default="project")
    post_policy: Mapped[str] = mapped_column(String(32), default="members")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_attachments: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_voice_notes: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_calls: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_video_calls: Mapped[bool] = mapped_column(Boolean, default=True)
    message_moderation_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_message_preview: Mapped[str | None] = mapped_column(String(512))
    last_message_author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project | None] = relationship(lazy="selectin")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id], lazy="selectin")
    members: Mapped[list[User]] = relationship(secondary=chatter_members, back_populates="chatters", lazy="selectin")
    messages: Mapped[list["Message"]] = relationship(back_populates="chatter", cascade="all, delete-orphan")


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chatter_id: Mapped[int] = mapped_column(ForeignKey("chatters.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    body: Mapped[str] = mapped_column(Text)
    original_body: Mapped[str | None] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(32), default="text")
    is_moderated: Mapped[bool] = mapped_column(Boolean, default=False)
    moderation_reason: Mapped[str | None] = mapped_column(String(255))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_to_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), index=True)

    chatter: Mapped[Chatter] = relationship(back_populates="messages", lazy="selectin")
    sender: Mapped[User] = relationship(foreign_keys=[sender_id], lazy="selectin")
    deleted_by: Mapped[User | None] = relationship(foreign_keys=[deleted_by_id], lazy="selectin")
    reply_to: Mapped["Message | None"] = relationship("Message", remote_side=[id], lazy="selectin")
    attachments: Mapped[list["Attachment"]] = relationship(secondary=message_attachments, lazy="selectin")
    seen_by: Mapped[list[User]] = relationship(secondary=message_seen, lazy="selectin")


class Attachment(TimestampMixin, Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    storage_path: Mapped[str] = mapped_column(String(512))
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    chatter_id: Mapped[int | None] = mapped_column(ForeignKey("chatters.id", ondelete="SET NULL"), index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[User | None] = relationship(foreign_keys=[deleted_by_id], lazy="selectin")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    chatter_id: Mapped[int | None] = mapped_column(ForeignKey("chatters.id", ondelete="SET NULL"), index=True)
    activity_type: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    chatter_id: Mapped[int | None] = mapped_column(ForeignKey("chatters.id", ondelete="SET NULL"))
    email_from: Mapped[str | None] = mapped_column(String(255))
    email_to: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(255))
    body_excerpt: Mapped[str | None] = mapped_column(Text)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="received")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoginAudit(Base):
    __tablename__ = "login_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str | None] = mapped_column(String(255), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    availability_status: Mapped[str] = mapped_column(String(32), default="online")
    idle_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(String(255))


class SignupRequest(TimestampMixin, Base):
    __tablename__ = "signup_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    login: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    requested_role: Mapped[str] = mapped_column(String(64), default="customer")
    note: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(32), default="pending")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    processed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AccessRequest(TimestampMixin, Base):
    __tablename__ = "access_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resource_type: Mapped[str] = mapped_column(String(32), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    chatter_id: Mapped[int | None] = mapped_column(ForeignKey("chatters.id", ondelete="CASCADE"), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    processed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requester: Mapped[User] = relationship(foreign_keys=[requester_id], lazy="selectin")
    processed_by: Mapped[User | None] = relationship(foreign_keys=[processed_by_id], lazy="selectin")
    project: Mapped[Project | None] = relationship(lazy="selectin")
    chatter: Mapped[Chatter | None] = relationship(lazy="selectin")


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class NotificationPreference(TimestampMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_notification_preferences_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    browser_push_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_chatter_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_workspace_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_chatter_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_workspace_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WebPushSubscription(TimestampMixin, Base):
    __tablename__ = "web_push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(Text)
    auth: Mapped[str] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TypingState(Base):
    __tablename__ = "typing_states"
    __table_args__ = (UniqueConstraint("chatter_id", "user_id", name="uq_typing_chatter_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chatter_id: Mapped[int] = mapped_column(ForeignKey("chatters.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CallSignal(Base):
    __tablename__ = "call_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    chatter_id: Mapped[int] = mapped_column(ForeignKey("chatters.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    signal_type: Mapped[str] = mapped_column(String(32))
    call_type: Mapped[str] = mapped_column(String(32), default="voice")
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OpsTask(TimestampMixin, Base):
    __tablename__ = "ops_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(String(32), default="todo")
    priority: Mapped[str] = mapped_column(String(32), default="normal")
    deadline: Mapped[date | None] = mapped_column(Date)
    progress: Mapped[float] = mapped_column(Float, default=0.0)


class OpsDocument(TimestampMixin, Base):
    __tablename__ = "ops_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id", ondelete="SET NULL"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    tag_names: Mapped[str | None] = mapped_column(String(255))
    access_level: Mapped[str] = mapped_column(String(32), default="project")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class OpsIncident(TimestampMixin, Base):
    __tablename__ = "ops_incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("ops_tasks.id", ondelete="SET NULL"))
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(String(32), default="general")
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    state: Mapped[str] = mapped_column(String(32), default="new")
    description: Mapped[str | None] = mapped_column(Text)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_summary: Mapped[str | None] = mapped_column(Text)


class OpsKnowledgeArticle(TimestampMixin, Base):
    __tablename__ = "ops_knowledge_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    state: Mapped[str] = mapped_column(String(32), default="draft")
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    revision_note: Mapped[str | None] = mapped_column(String(255))
