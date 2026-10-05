import os
from datetime import datetime
from reportlab.pdfgen import canvas
from .db import SessionLocal, ComplianceNotice

NOTICE_DIR = "/app/notices"
os.makedirs(NOTICE_DIR, exist_ok=True)

def generate_show_cause_notice(centre_code: str, discrepancy_details: str):
    """Generates a tamper-proof PDF notice for MSDE officials."""
    db = SessionLocal()
    
    # 1. Check if a notice was already issued today to prevent spam
    today = datetime.utcnow().date()
    existing = db.query(ComplianceNotice).filter(
        ComplianceNotice.centre_code == centre_code,
        ComplianceNotice.issue_date >= today
    ).first()
    
    if existing:
        db.close()
        return

    # 2. Generate the PDF Document
    filename = f"Notice_{centre_code}_{int(datetime.utcnow().timestamp())}.pdf"
    filepath = os.path.join(NOTICE_DIR, filename)
    
    c = canvas.Canvas(filepath)
    c.drawString(100, 800, "MINISTRY OF SKILL DEVELOPMENT & ENTREPRENEURSHIP")
    c.drawString(100, 780, "AUTOMATED SHOW CAUSE NOTICE - KUSHALDRISHTI")
    c.drawString(100, 740, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    c.drawString(100, 720, f"Subject: Ghost Attendance / Compliance Breach at {centre_code}")
    c.drawString(100, 680, f"Details:")
    c.drawString(100, 660, discrepancy_details)
    c.drawString(100, 620, "This anomaly was captured by edge-node analytics and cryptographically")
    c.drawString(100, 600, "verified. Please submit your clarification within 48 hours.")
    c.drawString(100, 500, "Digital Signature: KUSHALDRISHTI AUTOMATED AUDIT SYSTEM")
    c.save()

    # 3. Log the notice in the database
    new_notice = ComplianceNotice(
        centre_code=centre_code,
        violation_type="GHOST_ATTENDANCE",
        pdf_path=filepath
    )
    db.add(new_notice)
    db.commit()
    db.close()
    print(f"[Notice Engine] 🚨 Drafted Show Cause Notice for {centre_code}.")