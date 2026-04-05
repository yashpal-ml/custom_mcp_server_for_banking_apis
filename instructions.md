# Repository Instructions

## Purpose
`new_api_mcp` is a small MCP server that wraps a local FastAPI customer API and a few automation flows.

## Source of truth
- MCP tool definitions: [main.py](main.py)
- REST backend: [fastapi_app/app.py](fastapi_app/app.py)
- Request/response schemas: [fastapi_app/models.py](fastapi_app/models.py)
- App settings: [fastapi_app/config.py](fastapi_app/config.py)
- Playwright deposit automation: [scripts/xyz_bank_deposit.py](scripts/xyz_bank_deposit.py)
- MCP client/server wiring in VS Code: [.vscode/mcp.json](.vscode/mcp.json)

## Current MCP tools
1. `create_customer`
2. `get_customer`
3. `list_customers`
4. `create_savings_account`
5. `run_automation_maven_tests`
6. `run_xyz_bank_deposit`

## Architecture
- `main.py` exposes MCP tools via `FastMCP("new_api_mcp")`.
- Customer tools call the local FastAPI service at `http://127.0.0.1:9000/api/v1` using `httpx`.
- FastAPI stores customer/account data in memory only. Data resets on restart.
- `run_automation_maven_tests` executes Java/TestNG/Cucumber automation from `automation_mvn_tests/`.
- `run_xyz_bank_deposit` executes the Playwright Python script in `scripts/xyz_bank_deposit.py`.

## FastAPI behavior
- Health endpoint: `GET /health`
- Customer endpoints:
  - `POST /api/v1/customers`
  - `GET /api/v1/customers/{customer_id}`
  - `GET /api/v1/customers`
  - `POST /api/v1/customers/{customer_id}/accounts`
- `CustomerRequest.ssn` must match `XXX-XX-XXXX` when provided.
- `gender` must be one of: `Male`, `Female`, `Other`, `Prefer not to say`.

## Automation behavior
- `scripts/xyz_bank_deposit.py` deposits `$200` for `Hermoine Granger` on the GlobalSQA XYZ Bank demo.
- Script output is intentionally minimal:
  - `Starting balance`
  - `Deposited`
  - `Ending balance`
- `run_xyz_bank_deposit` parses that stdout into structured JSON.

## Working conventions
- Prefer editing `main.py`, `fastapi_app/*`, and `scripts/*`.
- Treat `automation_mvn_tests/target/`, `__pycache__/`, `.venv/`, and other generated artifacts as non-authoritative unless debugging execution output.
- Do not infer persistent storage; there is no database.
- Keep changes small and aligned with the current simple architecture.
- When adding new MCP tools, return structured JSON strings and follow the existing timeout/error-handling pattern.
- To perform a deposit transaction, use the `/xyz-deposit-txn` prompt.

## Runtime assumptions
- Python dependencies come from [pyproject.toml](pyproject.toml).
- VS Code MCP config starts:
  - Playwright MCP via `npx @playwright/mcp@latest`
  - `new_api_mcp` via `uv run main.py`
- The FastAPI app must be running separately for customer/account MCP tools to succeed.

## What to ignore unless explicitly requested
- `automation_mvn_tests/target/` reports
- notebook outputs in [test.ipynb](test.ipynb)
- sample files under `TEST_FILES/`
- cached/generated files under `__pycache__/`
