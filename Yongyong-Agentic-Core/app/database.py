# app/database.py
from sqlalchemy import create_engine, Column, Integer, Float, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./y_insight.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DesignHistory(Base):
    __tablename__ = "design_history"
    id = Column(Integer, primary_key=True, index=True)
    brightness = Column(Float)
    complexity = Column(Float)
    description = Column(Text) # AI 피드백 JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CoffeeLog(Base):
    __tablename__ = "coffee_log"
    id = Column(Integer, primary_key=True, index=True)
    caffeine_mg = Column(Integer)
    drink_type = Column(String)
    body_reaction = Column(String) # 예: "두통", "피로"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 테이블 생성
Base.metadata.create_all(bind=engine)