from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None


class UserBase(BaseModel):
    name: str
    login: str | None = None
    email: EmailStr
    phone: str | None = None
    active: bool = True
    roles: list[str] = Field(default_factory=list)


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    name: str | None = None
    login: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = Field(default=None, min_length=8)
    active: bool | None = None
    messenger_status: str | None = None
    roles: list[str] | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    login: str
    email: EmailStr
    active: bool
    phone: str | None = None
    messenger_status: str
    roles: list[RoleOut] = []
    created_at: datetime


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProjectBase(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    status: str = "active"
    priority: str = "normal"
    stage: str = "planning"
    start_date: date | None = None
    deadline: date | None = None
    completion_rate: float = 0.0
    manager_id: int | None = None
    customer_id: int | None = None
    member_ids: list[int] = Field(default_factory=list)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    stage: str | None = None
    start_date: date | None = None
    deadline: date | None = None
    completion_rate: float | None = None
    manager_id: int | None = None
    customer_id: int | None = None
    member_ids: list[int] | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str | None = None
    description: str | None = None
    status: str
    priority: str
    stage: str
    start_date: date | None = None
    deadline: date | None = None
    completion_rate: float
    manager_id: int | None = None
    customer_id: int | None = None
    members: list[UserOut] = []
    created_at: datetime


class ChatterBase(BaseModel):
    name: str
    description: str | None = None
    project_id: int | None = None
    conversation_type: str = "group"
    channel_scope: str = "project"
    post_policy: str = "members"
    allow_attachments: bool = True
    allow_voice_notes: bool = True
    allow_calls: bool = True
    allow_video_calls: bool = True
    member_ids: list[int] = Field(default_factory=list)


class ChatterCreate(ChatterBase):
    pass


class ChatterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    project_id: int | None = None
    conversation_type: str | None = None
    channel_scope: str | None = None
    post_policy: str | None = None
    active: bool | None = None
    allow_attachments: bool | None = None
    allow_voice_notes: bool | None = None
    allow_calls: bool | None = None
    allow_video_calls: bool | None = None
    member_ids: list[int] | None = None


class ChatterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    project_id: int | None = None
    created_by_id: int | None = None
    conversation_type: str
    channel_scope: str
    post_policy: str
    active: bool
    allow_attachments: bool
    last_message_preview: str | None = None
    last_activity: datetime | None = None
    unread_count: int = 0
    members: list[UserOut] = []
    created_at: datetime


class MessageCreate(BaseModel):
    body: str
    message_type: str = "text"
    attachment_ids: list[int] = Field(default_factory=list)
    reply_to_id: int | None = None


class MessageUpdate(BaseModel):
    body: str | None = None
    is_moderated: bool | None = None
    moderation_reason: str | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    content_type: str
    size_bytes: int
    project_id: int | None = None
    chatter_id: int | None = None
    uploaded_by_id: int | None = None
    is_deleted: bool = False
    deleted_by_id: int | None = None
    deleted_at: datetime | None = None
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    chatter_id: int
    sender_id: int
    body: str
    message_type: str
    is_moderated: bool
    moderation_reason: str | None = None
    attachments: list[AttachmentOut] = []
    seen_by: list[UserOut] = []
    is_deleted: bool = False
    deleted_by_id: int | None = None
    deleted_by_name: str | None = None
    deleted_at: datetime | None = None
    reply_to_id: int | None = None
    reply_to_sender_id: int | None = None
    reply_to_sender_name: str | None = None
    reply_to_body: str | None = None
    created_at: datetime


class GenericLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    body: str | None = None
    is_read: bool
    created_at: datetime


class InboundEmail(BaseModel):
    email_from: str | None = None
    email_to: str | None = None
    subject: str | None = None
    body: str | None = None
    project_id: int | None = None
    chatter_id: int | None = None
    attachment_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
