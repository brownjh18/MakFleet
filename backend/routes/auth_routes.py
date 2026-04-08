"""
MakFleet Authentication Routes
Handles user login, logout, registration, and profile management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from ..auth import (
    User, UserCreate, UserLogin, Token, TokenData,
    PasswordResetRequest, PasswordResetVerify, PasswordResetCode,
    authenticate_user, create_access_token, get_password_hash,
    get_current_user, init_default_users, verify_password,
    get_db, oauth2_scheme
)
from ..database import SessionLocal

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token
    """
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active
        }
    }


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Validate role
    if user_data.role not in ["admin", "driver"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'admin' or 'driver'"
        )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        driver_license=user_data.driver_license
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token for auto-login
    access_token = create_access_token(
        data={"sub": new_user.username, "role": new_user.role}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "is_active": new_user.is_active
        }
    }


class UserUpdate(BaseModel):
    """User update model"""
    full_name: Optional[str] = None
    email: Optional[str] = None
    driver_license: Optional[str] = None


@router.get("/me", response_model=dict)
def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "driver_license": current_user.driver_license,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }


@router.put("/me")
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile
    """
    # Update fields if provided
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    
    if user_data.email is not None:
        # Check if email is already taken by another user
        existing = db.query(User).filter(User.email == user_data.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = user_data.email
    
    if user_data.driver_license is not None:
        current_user.driver_license = user_data.driver_license
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Profile updated successfully",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "driver_license": current_user.driver_license
        }
    }


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user)):
    """
    Logout user (invalidate token on client side)
    """
    return {"message": "Logged out successfully"}


@router.put("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/check")
def check_auth(current_user: Optional[User] = Depends(get_current_user)):
    """
    Check if user is authenticated
    """
    if current_user is None:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "role": current_user.role
        }
    }


import random
from datetime import datetime, timedelta


def generate_reset_code() -> str:
    """Generate a 6-digit reset code"""
    return str(random.randint(100000, 999999))


def send_email_code(email: str, code: str):
    """
    Send verification code via email.
    In production, this would use an email service like SendGrid, AWS SES, etc.
    For now, we'll log the code to console for testing.
    """
    # In production, implement actual email sending here
    # For example with smtplib:
    # import smtplib
    # from email.message import EmailMessage
    # msg = EmailMessage()
    # msg.set_content(f"Your password reset code is: {code}")
    # msg['Subject'] = 'MakFleet Password Reset'
    # msg['From'] = 'noreply@makfleet.ac.ug'
    # msg['To'] = email
    # 
    # with smtplib.SMTP('smtp.gmail.com', 587) as server:
    #     server.starttls()
    #     server.login('your-email@gmail.com', 'your-password')
    #     server.send_message(msg)
    
    # For development/testing, log the code
    print(f"\n{'='*50}")
    print(f"EMAIL VERIFICATION CODE for {email}: {code}")
    print(f"{'='*50}\n")
    
    return True


@router.post("/forgot-password")
def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Request a password reset code via email
    """
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a reset code has been sent."}
    
    # Generate reset code
    code = generate_reset_code()
    
    # Create password reset code record
    reset_code = PasswordResetCode(
        email=request.email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=15)  # Code expires in 15 minutes
    )
    db.add(reset_code)
    db.commit()
    
    # Send email with code
    send_email_code(request.email, code)
    
    return {"message": "If the email exists, a reset code has been sent."}


@router.post("/reset-password")
def reset_password(request: PasswordResetVerify, db: Session = Depends(get_db)):
    """
    Reset password using verification code
    """
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or code"
        )
    
    # Find valid reset code
    reset_code = db.query(PasswordResetCode).filter(
        PasswordResetCode.email == request.email,
        PasswordResetCode.code == request.code,
        PasswordResetCode.is_used == False,
        PasswordResetCode.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )
    
    # Validate new password
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    
    # Mark reset code as used
    reset_code.is_used = True
    
    db.commit()
    
    return {"message": "Password reset successfully"}


# Note: Router startup events are not supported.
# Default users are initialized in backend/main.py startup event.
