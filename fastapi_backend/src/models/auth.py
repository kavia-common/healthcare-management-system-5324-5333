from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


class LoginRequest(BaseModel):
    username: str = Field(..., description="Email as username")
    password: str = Field(..., description="User password")
