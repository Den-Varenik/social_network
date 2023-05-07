from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, APIRouter, Header
from fastapi.param_functions import Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session
from config.settings import settings
from models.users import User
from schemas.auth import Token, RefreshToken, CreateAuthUserSchema

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/create")

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_jwt_token(user_id: id, expires_delta: timedelta) -> str:
    to_encode = {"user_id": user_id, "exp": datetime.utcnow() + expires_delta}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["user_id"]
        return {"user_id": user_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


async def fetch_user(session: AsyncSession, error_message: str, user_id: int = None, email: str = None) -> User:
    if user_id is not None:
        result = await session.execute(select(User).where(User.id == user_id))
    elif email is not None:
        result = await session.execute(select(User).where(User.email == email))
    else:
        raise ValueError("Either user_id or email must be provided")
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=error_message)
    return user


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User:
    error_message = "Incorrect username or password"
    user = await fetch_user(session, error_message=error_message, email=username)
    if not user.check_password(password):
        raise HTTPException(status_code=401, detail=error_message)
    return user


class EmailPasswordRequestForm:
    def __init__(
        self,
        email: str = Form(),
        password: str = Form(),
    ):
        self.email = email
        self.password = password


@router.post("/create", response_model=Token)
async def jwt_create(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                     session: AsyncSession = Depends(get_async_session)):
    user = await authenticate_user(session, form_data.username, form_data.password)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_jwt_token(user.id, access_token_expires)
    refresh_token = create_jwt_token(user.id, refresh_token_expires)
    return {"access_token": access_token, "refresh_token": refresh_token}


@router.post("/refresh", response_model=Token)
async def jwt_refresh(token: RefreshToken, session: AsyncSession = Depends(get_async_session)):
    try:
        payload = verify_jwt_token(token.refresh_token)
        user_id = payload["user_id"]

        user = await fetch_user(session, user_id=user_id, error_message="Token is invalid")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        access_token = create_jwt_token(user.id, access_token_expires)
        refresh_token = create_jwt_token(user.id, refresh_token_expires)
        return {"access_token": access_token, "refresh_token": refresh_token}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/verify", status_code=200)
async def jwt_verify(authorization: str = Header(...), session: AsyncSession = Depends(get_async_session)):
    try:
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        payload = verify_jwt_token(token)
        user_id = payload["user_id"]
        await fetch_user(session, user_id=user_id, error_message="Token is invalid")
    except (ValueError, KeyError, JWTError):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/register", response_model=Token)
async def register_user(user: CreateAuthUserSchema, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User).where(User.email == user.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        is_verified=False,
        account_type=user.account_type,
        created_at=datetime.utcnow()
    )
    new_user.set_password(user.password)
    session.add(new_user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_jwt_token(new_user.id, access_token_expires)
    refresh_token = create_jwt_token(new_user.id, refresh_token_expires)
    return {"access_token": access_token, "refresh_token": refresh_token}


async def current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_async_session)):
    data = verify_jwt_token(token)
    user = await fetch_user(session, error_message="User not found", user_id=data.get('user_id'))
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
