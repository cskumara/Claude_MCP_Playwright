# CLAUDE.md

Login demo used to practice test -> reproduce -> debug -> fix with Playwright MCP. See `Spec.md`.

## Layout
- `app/server.py` Flask app (port 3000); `app/templates/login.html`; `app/static/login.js`
- `tests/e2e/` pytest + playwright tests (`conftest.py` starts the server)
- `screenshots/` browser evidence
- `.mcp.json` Playwright MCP config

## Commands
- Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/playwright install chromium`
- Run app: `.venv/bin/python app/server.py` (http://localhost:3000/login)
- Test: `.venv/bin/pytest` (single: `.venv/bin/pytest tests/e2e/test_login.py`)

## Rules
- Local environment and test credentials only.
- Never edit or delete a test just to make it pass.
- Tests use `get_by_label` / `get_by_role`; no CSS selectors, no sleeps.
- Smallest fix in the right place. If stuck after 3 attempts, stop and report.
- Commit messages explain the root cause.
