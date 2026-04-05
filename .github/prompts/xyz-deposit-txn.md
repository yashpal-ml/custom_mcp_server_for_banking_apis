---
name: savings-account-deposit
description: "Use when: running an XYZ Bank deposit transaction for a customer"
---

You are executing a two-step banking workflow using the `new_api_mcp` MCP server.

## Inputs

- None. Do not take any user input. Just execute the steps mentioned in the xyz_bank_deposit.py script with default parameters using the Playwright MCP tool.

## Steps

1. **Run deposit** — Call `run_xyz_bank_deposit` with default parameters (`headless: false`).
   - This executes `scripts/xyz_bank_deposit.py` directly using Playwright MCP and returns the deposit transaction result.

## Output

After both steps complete, summarize:
- The deposit result (`starting_balance`, `deposited_amount`, `ending_balance`) from `run_xyz_bank_deposit`
