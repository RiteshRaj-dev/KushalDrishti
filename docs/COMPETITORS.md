# Existing solutions and the gap (based on public descriptions; verify before presenting)
Sources: MSDE reply in Lok Sabha Q.2099 (9 Dec 2024) on PMKVY 4.0 monitoring, and the NSDC notice on AEBAS (1 Mar 2022).
| Existing solution | What it does | Gap KushalDrishti fills |
|---|---|---|
| AEBAS (Aadhaar biometric attendance) | Records identity punches | A punch is not who stays in the room, and it checks no equipment |
| Call validation, surprise visits | Manual checks | Periodic, cannot watch every centre every day |
| Virtual verification (geotagged photos on request) | Centre sends a photo when asked | Centre chooses the moment and the angle |
| CCTV people counters | Count people per camera | Not linked to scheme records, no equipment check |
| Face-recognition attendance | Identifies people | Conflicts with the problem statement's privacy aim |
| Frigate, Roboflow Supervision | Detection and counting building blocks | No reconciliation, offline buffer, signed log or map |
| **KushalDrishti** | Counts as a number, checks equipment, compares with portal records, works offline, signed log, national map, officer approval | See README for what is tested |
It works WITH AEBAS: AEBAS punches can be the claimed number that KushalDrishti checks against the room.
