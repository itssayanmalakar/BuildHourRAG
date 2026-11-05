PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)

.PHONY: install ingest chunk embed index build run test eval sources doctor clean

install:
	$(PY) -m pip install -r requirements.txt && $(PY) -m pip install -e .

ingest:
	$(PY) -m mf_facts.cli ingest

chunk:
	$(PY) -m mf_facts.cli chunk

embed:
	$(PY) -m mf_facts.cli embed

index:
	$(PY) -m mf_facts.cli index

build:
	$(PY) -m mf_facts.cli build --use-cache

run:
	$(PY) -m streamlit run app.py

test:
	$(PY) -m pytest -q

eval:
	$(PY) -m mf_facts.cli eval

sources:
	$(PY) scripts/gen_sources.py

doctor:
	$(PY) -m mf_facts.cli doctor

clean:
	$(PY) -m mf_facts.cli reset
