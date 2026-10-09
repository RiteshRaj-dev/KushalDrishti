"""Draft Show Cause Notice. It is a DRAFT for an officer, never an automatic penalty."""
import hashlib, io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

KIND_TEXT = {
    "GHOST_ATTENDANCE": "The number of trainees counted in the training room stayed well below the attendance filed on the portal for the full review period.",
    "EQUIPMENT_MISSING": "One or more items on the sanctioned equipment list were not seen by the camera in the review period.",
}

def build_notice(alert, packet, centre, evidence_file, approved):
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    def mark(canvas, doc):
        canvas.saveState()
        if not approved:
            canvas.setFont("Helvetica-Bold", 60); canvas.setFillColor(colors.Color(0.9, 0.3, 0.2, alpha=0.12))
            canvas.translate(10.5 * cm, 14 * cm); canvas.rotate(45); canvas.drawCentredString(0, 0, "DRAFT")
        canvas.restoreState()
        canvas.setFont("Helvetica", 7); canvas.setFillColor(colors.grey)
        canvas.drawString(2 * cm, 1.2 * cm, f"Packet signature: {packet['sig']}")
        canvas.drawString(2 * cm, 0.8 * cm, "Automated finding from camera counts. Not conclusive until verified by an officer.")
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    s = [Paragraph("DRAFT SHOW CAUSE NOTICE", styles["Title"]),
         Paragraph(f"Notice reference: KD/{alert['id']:06d} &nbsp;&nbsp; Date: {datetime.now():%d %b %Y}", styles["Normal"]), Spacer(1, 10)]
    t = Table([["Centre", f"{centre['name']} ({centre['code']})"], ["State", centre["state"]],
               ["Finding", alert["kind"].replace("_", " ").title()],
               ["Claimed on portal", str(packet["claimed"])],
               ["Counted (average)", "n/a" if packet["headcount"] is None else f"{packet['headcount']:.1f}"],
               ["Camera status", str(packet["camera_health"])],
               ["Equipment", ", ".join(f"{k}: {v}" for k, v in (packet["equipment"] or {}).items())],
               ["Seen at", f"{packet['ts']:%d %b %Y %H:%M} UTC"]], colWidths=[4*cm, 12*cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey), ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    s += [t, Spacer(1, 10), Paragraph(KIND_TEXT.get(alert["kind"], ""), styles["Normal"]), Spacer(1, 8),
          Paragraph("The centre is requested to explain this difference within the period set by the issuing officer.", styles["Normal"]), Spacer(1, 10)]
    if evidence_file:
        s += [Paragraph("Evidence photo (faces blurred):", styles["Normal"]), Image(evidence_file, width=12*cm, height=7*cm, kind="proportional")]
    else:
        s.append(Paragraph("No evidence photo was received for this packet.", styles["Normal"]))
    s.append(Spacer(1, 20))
    if approved:
        s.append(Paragraph(f"Reviewed by officer: {alert['reviewed_by']} on {alert['reviewed_at']:%d %b %Y}", styles["Normal"]))
    else:
        s.append(Paragraph("Status: waiting for officer review. Sign only after checking the evidence.", styles["Normal"]))
    s += [Spacer(1, 30), Paragraph("Signature of issuing officer: ____________________", styles["Normal"])]
    doc.build(s, onFirstPage=mark, onLaterPages=mark)
    data = buf.getvalue()
    return data, hashlib.sha256(data).hexdigest()
