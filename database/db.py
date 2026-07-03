# database/db.py

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DB_PATH = os.path.join(os.path.dirname(__file__), "jobsearcher.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    location = Column(String, default="Lahore")
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    password_resets = relationship(
        "PasswordReset",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    searches = relationship("JobSearch", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    cover_letters = relationship("CoverLetter", back_populates="user", cascade="all, delete-orphan")

    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    parsed_text = Column(Text)
    extracted_skills = Column(Text)
    extracted_roles = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")


class JobSearch(Base):
    __tablename__ = "job_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    location = Column(String)
    jobs_found = Column(Text)
    top_matches = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="searches")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_title = Column(String)
    company = Column(String)
    job_url = Column(String)
    cover_letter = Column(Text)
    status = Column(String, default="pending")
    notes = Column(Text)
    applied_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="applications")


class CoverLetter(Base):
    __tablename__ = "cover_letters"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    
    job_title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    job_description = Column(Text)
    job_url = Column(String)
    
    variants = Column(JSON)
    selected_variant = Column(Integer)
    final_text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="cover_letters")
    resume = relationship("Resume")
    
    def __repr__(self):
        return f"<CoverLetter {self.id}: {self.job_title} at {self.company}>"


# ✅ PasswordReset defined HERE (after Base, before other models that reference it)
class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="password_resets")
    
    def __repr__(self):
        return f"<PasswordReset user_id={self.user_id}>"
    
    def is_valid(self):
        """Check if token is still valid"""
        return (
            not self.used 
            and datetime.utcnow() < self.expires_at
        )


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "Base", "engine", "SessionLocal", "get_db",
    "User", "Resume", "JobSearch", "Application",
    "CoverLetter", "PasswordReset"
]