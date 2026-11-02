# Launch this workflow through Crucible in Linux/WSL.
IGNY ?= igny
IGNY_ENV ?= formal-fifo
IGNY_SCRIPT = $(IGNY) run script --env $(IGNY_ENV)
.DEFAULT_GOAL := help
.NOTPARALLEL:
.PHONY: help setup check sed build run smoke report preflight identity broken prove cover sim

help:
	@echo "igny run --env $(IGNY_ENV) make run - execute the complete experiment and independent checks"
	@echo "igny run --env $(IGNY_ENV) make build - prepare the project build artifacts"
	@echo "igny run --env $(IGNY_ENV) make smoke - verify existing results; does not rebuild"
	@echo "igny run --env $(IGNY_ENV) make setup - prepare pinned project-local observer dependencies"
	@echo "igny run --env $(IGNY_ENV) make check - check Python observer imports"
	@echo "igny run --env $(IGNY_ENV) make sed - normalise public shell inputs to LF"
	@echo "igny run --env $(IGNY_ENV) make report - print generated result summaries"
	@echo "igny run --env $(IGNY_ENV) make preflight - review public package paths, links and hashes"

setup:
	$(IGNY_SCRIPT) scripts/demo_info.py -- setup

check:
	$(IGNY_SCRIPT) scripts/demo_info.py -- check

sed:
	$(IGNY_SCRIPT) scripts/demo_info.py -- normalise

report:
	$(IGNY_SCRIPT) scripts/demo_info.py -- report

preflight:
	$(IGNY_SCRIPT) scripts/preflight_git.py

build: sed identity prove cover

run: sed check identity broken prove cover sim smoke

identity:
	$(IGNY_SCRIPT) scripts/run.sh -- identity

broken:
	$(IGNY_SCRIPT) scripts/run.sh -- broken

prove:
	$(IGNY_SCRIPT) scripts/run.sh -- prove

cover:
	$(IGNY_SCRIPT) scripts/run.sh -- cover

sim:
	$(IGNY_SCRIPT) scripts/run.sh -- sim

smoke:
	$(IGNY_SCRIPT) scripts/demo_info.py -- verify
