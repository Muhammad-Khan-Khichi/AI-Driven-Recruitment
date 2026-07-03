from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
# from database.db import Base
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Secure random token (hashed in DB)
    token = Column(String, unique=True, index=True, nullable=False)
    
    # Expiration time
    expires_at = Column(DateTime, nullable=False)
    
    # Track if used (prevent reuse)
    used = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to User
    user = relationship("User", back_populates="password_resets")
    
    def __repr__(self):
        return f"<PasswordReset user_id={self.user_id}>"
    
    def is_valid(self):
        """Check if token is still valid"""
        return (
            not self.used 
            and datetime.utcnow() < self.expires_at
        )