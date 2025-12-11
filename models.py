# models.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import re, secrets

Base = declarative_base()
DB_URL = "sqlite:///unbound.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    api_key = Column(String, unique=True)
    role = Column(String)  # admin or member
    credits = Column(Integer, default=100)

# Command model
class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    command_text = Column(Text)
    status = Column(String)  # executed, rejected
    reason = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

# Rule model
class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String)
    action = Column(String)  # AUTO_ACCEPT, AUTO_REJECT

# Initialize DB and seed admin + rules
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create default admin if not exists
    if not db.query(User).filter_by(role="admin").first():
        admin_api_key = secrets.token_urlsafe(16)
        admin = User(username="admin", api_key=admin_api_key, role="admin", credits=1000)
        db.add(admin)
        db.commit()
        print(f"Admin created! API Key: {admin_api_key}")

    # Seed starter rules
    starter_rules = [
        (r":\(\)\{ :\|:& \};:", "AUTO_REJECT"),
        (r"rm\s+-rf\s+/", "AUTO_REJECT"),
        (r"mkfs\.", "AUTO_REJECT"),
        (r"git\s+(status|log|diff)", "AUTO_ACCEPT"),
        (r"^(ls|cat|pwd|echo)", "AUTO_ACCEPT"),
    ]
    for pattern, action in starter_rules:
        if not db.query(Rule).filter_by(pattern=pattern).first():
            db.add(Rule(pattern=pattern, action=action))
    db.commit()
    db.close()
