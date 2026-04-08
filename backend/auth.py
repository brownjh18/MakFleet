"""
MakFleet Authentication & Authorization Module
Implements role-based access control (RBAC) with two roles: admin and driver
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "makfleet-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing - use sha256_crypt as fallback for bcrypt compatibility
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# Pydantic models (no database dependency)
class Token(BaseModel):
    """JWT Token response model"""
    access_token: str
    token_type: str
    user: dict


class TokenData(BaseModel):
    """JWT Token data model"""
    username: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    """User creation model"""
    username: str
    email: str
    password: str
    full_name: str
    role: str = "driver"
    driver_license: Optional[str] = None


class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: str


class PasswordResetVerify(BaseModel):
    """Password reset verify model"""
    email: str
    code: str
    new_password: str


class User(BaseModel):
    """User model for authentication (simplified without DB dependency)"""
    id: int = 0
    username: str
    email: str
    full_name: str
    role: str = "driver"
    is_active: bool = True
    driver_license: Optional[str] = None
    assigned_vehicle_id: Optional[int] = None


class PasswordResetCode(BaseModel):
    """Password reset code model (simplified without DB dependency)"""
    id: int = 0
    email: str
    code: str
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_used: bool = False


# Lazy imports to avoid circular dependencies
def _get_base():
    """Lazy import of Base to avoid circular imports"""
    from .base import Base
    return Base


def _get_SessionLocal():
    """Lazy import of SessionLocal to avoid circular imports"""
    from .database import SessionLocal
    return SessionLocal


def _get_User_model():
    """Lazy import of User model to avoid circular imports"""
    from .base import Base
    from sqlalchemy import Column, Integer, String, Boolean, DateTime
    
    # Check if User is already defined in Base
    if hasattr(Base.registry, 'classes'):
        for cls in Base.registry.classes:
            if getattr(cls, '__tablename__', None) == 'users':
                return cls
    
    # Define User model
    class User(Base):
        """User model for authentication"""
        __tablename__ = "users"
        
        id = Column(Integer, primary_key=True, index=True)
        username = Column(String(50), unique=True, nullable=False, index=True)
        email = Column(String(100), unique=True, nullable=False)
        hashed_password = Column(String(256), nullable=False)
        full_name = Column(String(100), nullable=False)
        role = Column(String(20), nullable=False)  # 'admin' or 'driver'
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        last_login = Column(DateTime, nullable=True)
        
        # Driver-specific fields (nullable for admin users)
        driver_license = Column(String(50), nullable=True)
        assigned_vehicle_id = Column(Integer, nullable=True)
    
    return User


def _get_PasswordResetCode_model():
    """Lazy import of PasswordResetCode model to avoid circular imports"""
    from .base import Base
    from sqlalchemy import Column, Integer, String, Boolean, DateTime
    
    # Check if PasswordResetCode is already defined in Base
    if hasattr(Base.registry, 'classes'):
        for cls in Base.registry.classes:
            if getattr(cls, '__tablename__', None) == 'password_reset_codes':
                return cls
    
    # Define PasswordResetCode model
    class PasswordResetCode(Base):
        """Password reset code model"""
        __tablename__ = "password_reset_codes"
        
        id = Column(Integer, primary_key=True, index=True)
        email = Column(String(100), nullable=False, index=True)
        code = Column(String(6), nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        expires_at = Column(DateTime, nullable=False)
        is_used = Column(Boolean, default=False)
    
    return PasswordResetCode


# Functions that need database
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user by username and password"""
    User = _get_User_model()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def get_db():
    """Get database session"""
    SessionLocal = _get_SessionLocal()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[object]:
    """Get the current user from JWT token"""
    if token is None:
        return None
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    
    User = _get_User_model()
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    return user


def require_role(required_role: str):
    """Dependency to require a specific role"""
    async def role_checker(
        current_user = Depends(get_current_user)
    ):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role",
            )
        return current_user
    return role_checker


def init_default_users(db: Session):
    """Initialize default users if they don't exist"""
    Base = _get_base()
    User = _get_User_model()
    
    # Create the users table if it doesn't exist
    try:
        Base.metadata.create_all(db.get_bind(), tables=[User.__table__])
    except Exception as e:
        print(f"Warning: Could not create users table: {e}")
        return
    
    # Check if admin user exists
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@makfleet.ac.ug",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            role="admin",
            is_active=True
        )
        db.add(admin)
        print("Created default admin user (username: admin, password: admin123)")
    
    # Check if driver user exists
    driver = db.query(User).filter(User.username == "driver").first()
    if not driver:
        driver = User(
            username="driver",
            email="driver@makfleet.ac.ug",
            hashed_password=get_password_hash("driver123"),
            full_name="Demo Driver",
            role="driver",
            is_active=True,
            driver_license="UGA-DL-001234"
        )
        db.add(driver)
        print("Created default driver user (username: driver, password: driver123)")
    
    db.commit()