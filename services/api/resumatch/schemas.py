from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

Short = Annotated[str, Field(max_length=200)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(Input):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Start(Input):
    intention: str = Field(min_length=1, max_length=200)
    target_minutes: int = Field(default=25, ge=5, le=180)
    workflow_id: UUID | None = None
    run_name: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("run_name", mode="before")
    @classmethod
    def optional_run_name(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class Transition(Input):
    action: Literal["pause", "resume", "finish", "complete"]


class Details(Input):
    source_url: HttpUrl
    source_title: str = Field(default="", max_length=500)
    quote: str = Field(default="", max_length=4000)
    person: Short = ""
    company: Short = ""
    channel: Literal["linkedin", "email", "x", "web", "other"] = "linkedin"
    action: Literal[
        "researched", "drafted", "connection_requested", "sent", "followed_up", "replied"
    ] = "researched"
    notes: str = Field(default="", max_length=16000)
    fields: dict[str, str | int | float | bool | None] = Field(default_factory=dict, max_length=20)
    occurred_at: datetime | None = None
    followup_on: date | None = None

    @field_validator("source_url")
    @classmethod
    def clean_url(cls, value):
        if value.username or value.password:
            raise ValueError("Source URLs must not contain credentials")
        return value

    @field_validator("occurred_at")
    @classmethod
    def timestamp(cls, value):
        if value and (value.tzinfo is None or value > datetime.now(UTC) + timedelta(minutes=5)):
            raise ValueError("Use a timezone-aware activity time that is not in the future")
        return value


class CaptureInput(Input):
    request_id: UUID
    details: Details


class EditCapture(Input):
    details: Details


class Review(Input):
    decision: Literal["approved", "discarded"]
    details: Details
    confirmed_action: bool = False


class BulkApprove(Input):
    # The exact records the user saw; records captured afterwards are never swept in.
    capture_ids: list[UUID] = Field(min_length=1, max_length=500)


class PairInput(Input):
    extension_id: str = Field(pattern=r"^[a-p]{32}$")


class Goal(Input):
    weekly_target: int = Field(ge=1, le=14)
