from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str


class RefreshToken(BaseModel):
    refresh_token: str


class AuthUserSchema(BaseModel):
    email: str
    password: str


class CreateAuthUserSchema(BaseModel):
    email: EmailStr
    password: str
