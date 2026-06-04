.PHONY: bootstrap verify-phase0 verify-all verify-all-live install dry-run crawl-only

bootstrap:
	@bash scripts/bootstrap.sh

verify-phase0:
	@./venv/bin/python scripts/verify_phase0.py 2>/dev/null || python3 scripts/verify_phase0.py

verify-all:
	@./venv/bin/python scripts/verify_phases.py 2>/dev/null || python3 scripts/verify_phases.py

verify-all-live:
	@./venv/bin/python scripts/verify_phases.py --live

install:
	python3 -m venv venv
	./venv/bin/python -m pip install -q --upgrade "pip>=23.0" setuptools wheel
	./venv/bin/pip install -q -r requirements.txt
	./venv/bin/pip install -q -e .

dry-run:
	./venv/bin/python -m ai_news_bot.main --dry-run --preview-card output/card.json

crawl-only:
	./venv/bin/python -m ai_news_bot.main --crawl-only

run:
	./venv/bin/python -m ai_news_bot.main --log-file logs/brief.log
