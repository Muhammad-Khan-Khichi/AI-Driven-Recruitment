from database.db import Base, engine, SessionLocal, User, Resume, JobSearch, Application

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()