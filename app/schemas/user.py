"""Pydantic schemas for user endpoints."""

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    user_id: str = Field(..., min_length=1, max_length=36)
    name: str = Field(..., min_length=1, max_length=256)
    email: str = Field(..., min_length=5, max_length=256)
    phone: str = Field(..., min_length=10, max_length=20)
    location: str = Field(..., min_length=1, max_length=256)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class UserResponse(UserCreate):
    """Schema for user response."""

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """List of users."""

    users: list[UserResponse]
    total: int
