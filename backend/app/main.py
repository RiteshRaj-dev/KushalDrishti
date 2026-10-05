from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .db import get_db, ITICentre, TelemetryLog, ComplianceNotice
from .ingest import start_mqtt_listener

app = FastAPI(title="KushalDrishti MSDE API", version="2.0")

@app.on_event("startup")
def startup_event():
    """Boot up the MQTT Listener in the background."""
    start_mqtt_listener()

@app.get("/api/v1/map_data")
def get_national_map_data(db: Session = Depends(get_db)):
    """Returns geospatial data for all ITI centres and their latest status."""
    centres = db.query(ITICentre).all()
    results = []
    
    for c in centres:
        # Get the latest telemetry log for this centre
        latest_log = db.query(TelemetryLog)\
            .filter(TelemetryLog.centre_code == c.centre_code)\
            .order_by(TelemetryLog.timestamp.desc()).first()
            
        status = latest_log.status if latest_log else "UNKNOWN"
        presence = latest_log.counted_presence if latest_log else 0
        
        results.append({
            "centre_code": c.centre_code,
            "name": c.name,
            "state": c.state,
            "lat": c.latitude,
            "lng": c.longitude,
            "claimed_attendance": c.claimed_attendance,
            "actual_presence": presence,
            "status": status
        })
        
    return results

@app.get("/api/v1/notices")
def get_compliance_notices(db: Session = Depends(get_db)):
    """Returns all generated Show Cause Notices."""
    notices = db.query(ComplianceNotice).order_by(ComplianceNotice.issue_date.desc()).all()
    return [
        {
            "id": n.id,
            "centre_code": n.centre_code,
            "issue_date": str(n.issue_date),
            "violation": n.violation_type,
            "pdf_path": n.pdf_path
        } for n in notices
    ] 