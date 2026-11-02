from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PRIVACY_VERSION = "2026-11-02"


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128, repr=False)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value: str) -> str:
        return value.casefold()


class Registration(Credentials):
    password: str = Field(min_length=12, max_length=128, repr=False)
    accepted_privacy: Literal[True]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    external_ai_consent: bool


class SessionResponse(BaseModel):
    mode: Literal["local-demo", "authenticated"]
    user: UserResponse | None = None
    csrf_token: str | None = None
    registration_enabled: bool = False
    privacy_version: str = PRIVACY_VERSION


class PasswordConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    password: str = Field(min_length=1, max_length=128, repr=False)


class PasswordChange(PasswordConfirmation):
    new_password: str = Field(min_length=12, max_length=128, repr=False)


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: bool
