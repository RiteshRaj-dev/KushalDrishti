test:            ## all tests (cloud tests need PostGIS, otherwise they are skipped)
	python -m pytest -q tests
demo:            ## cloud + 12 simulated centres, then open http://localhost:8000
	docker compose --profile demo up --build
check:           ## list missing files before you build or push
	python check_files.py
