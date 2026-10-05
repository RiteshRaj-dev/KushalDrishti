import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://msde_admin:msde_password@db:5432/kushaldrishti")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 1. Master Registry of ITI Centres
class ITICentre(Base):
    __tablename__ = "iti_centres"
    
    centre_code = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    state = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    claimed_attendance = Column(Integer, default=0)

# 2. Real-Time Edge Telemetry Stream
class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    centre_code = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    counted_presence = Column(Float)
    status = Column(String)  # COMPLIANT, WARNING_SUSPECTED_GAP, BREACH_GHOST_ATTENDANCE
    equipment_status = Column(JSON)
    tamper_verified = Column(Boolean, default=True)

# 3. PDF Show Cause Notices
class ComplianceNotice(Base):
    __tablename__ = "compliance_notices"
    
    id = Column(Integer, primary_key=True, index=True)
    centre_code = Column(String, index=True)
    issue_date = Column(DateTime, default=datetime.utcnow)
    violation_type = Column(String)
    pdf_path = Column(String)

# Automatically create tables on boot
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()