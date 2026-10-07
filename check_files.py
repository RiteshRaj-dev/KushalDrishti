"""Run this BEFORE `docker compose up` and before `git push`. It lists anything missing."""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
REQUIRED = """README.md LICENSE NOTICE.md Makefile docker-compose.yml requirements.txt requirements-dev.txt .gitignore .github/workflows/ci.yml
shared/security.py data/centres.json mosquitto/mosquitto.conf
backend/__init__.py backend/Dockerfile backend/requirements.txt backend/app/__init__.py backend/app/main.py backend/app/db.py backend/app/ingest.py backend/app/notice.py
edge/Dockerfile edge/edge_node.py edge/run_fleet.py edge/kd_edge/__init__.py edge/kd_edge/config.py edge/kd_edge/privacy.py edge/kd_edge/health.py edge/kd_edge/rules.py edge/kd_edge/packets.py edge/kd_edge/transport.py edge/kd_edge/detectors.py edge/kd_edge/pipeline.py edge/kd_edge/run.py edge/kd_edge/evaluate.py edge/kd_edge/speed.py
dashboard/index.html tools/fill_deck.py notebooks/KushalDrishti_Colab.ipynb
tests/conftest.py tests/test_edge.py tests/test_cloud.py tests/test_deck_tool.py
docs/PRIVACY_NOTE.md docs/EVALUATION.md docs/COMPETITORS.md docs/DEPLOYMENT.md deck/SIH26245.pptx""".split()
missing = [f for f in REQUIRED if not os.path.isfile(os.path.join(ROOT, f))]
for f in missing:
    print("MISSING  " + f)
odd = [d for d in os.listdir(ROOT) if d.lower() in ("edge", "backend", "shared", "dashboard", "data", "tests", "tools", "docs") and d != d.lower()]
if odd:
    print("WRONG CASE (rename to lowercase):", odd)
if missing or odd:
    print(f"\n{len(missing)} file(s) missing. Copy them from the original zip, then run `git add -A` and push again."); sys.exit(1)
print(f"All {len(REQUIRED)} required files present.")
