"""Tool implementations for MCP server."""

import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Annotated

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("new_api_mcp")

base_url: str = "http://127.0.0.1:9000"
PROJECT_ROOT = Path(__file__).resolve().parent
AUTOMATION_MVN_TESTS_DIR = PROJECT_ROOT / "automation_mvn_tests"
# XYZ_BANK_DEPOSIT_SCRIPT = PROJECT_ROOT / "scripts" / "xyz_bank_deposit.py"
DEFAULT_TESTNG_SUITE = Path("src/test/resources/testng.xml")
ALLOWED_MAVEN_GOALS = {"test", "verify"}


def _tail_output(output: str, max_chars: int) -> str:
    """
    Return the last max_chars characters of the output, with a truncation notice if it was too long.
    """
    if len(output) <= max_chars:
        return output
    return f"... output truncated to last {max_chars} chars ...\n{output[-max_chars:]}"


def _normalize_stream(stream: str | bytes | None) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode(errors="replace")
    return stream


def _find_maven_command() -> list[str] | None:
    wrapper_candidates = [
        AUTOMATION_MVN_TESTS_DIR / "mvnw.cmd",
        AUTOMATION_MVN_TESTS_DIR / "mvnw.bat",
        AUTOMATION_MVN_TESTS_DIR / "mvnw",
        AUTOMATION_MVN_TESTS_DIR / "mvn.cmd"
    ]
    for candidate in wrapper_candidates:
        if candidate.is_file():
            return [str(candidate)]

    for executable in ("mvn", "mvn.cmd", "mvn.bat"):
        resolved = shutil.which(executable)
        if resolved:
            return [resolved]

    return None


def _resolve_suite_path(testng_suite: str) -> Path:
    suite_rel_path = Path(testng_suite.strip() or str(DEFAULT_TESTNG_SUITE))
    if suite_rel_path.is_absolute():
        raise ValueError("testng_suite must be a relative path under automation_mvn_tests")

    suite_abs_path = (AUTOMATION_MVN_TESTS_DIR / suite_rel_path).resolve()
    if not suite_abs_path.is_relative_to(AUTOMATION_MVN_TESTS_DIR.resolve()):
        raise ValueError("testng_suite must stay inside automation_mvn_tests")

    if not suite_abs_path.is_file():
        raise FileNotFoundError(f"TestNG suite not found: {suite_rel_path.as_posix()}")

    return suite_abs_path


def _collect_report_paths() -> list[str]:
    report_candidates = [
        AUTOMATION_MVN_TESTS_DIR / "target" / "surefire-reports" / "testng-results.xml",
        AUTOMATION_MVN_TESTS_DIR / "target" / "surefire-reports" / "emailable-report.html",
        AUTOMATION_MVN_TESTS_DIR / "target" / "cucumber.json",
        AUTOMATION_MVN_TESTS_DIR / "target" / "cucumber-reports",
    ]

    available_reports: list[str] = []
    for candidate in report_candidates:
        if candidate.exists():
            available_reports.append(candidate.relative_to(PROJECT_ROOT).as_posix())
    return available_reports


def _parse_script_output(output: str) -> dict[str, int | str]:
    parsed: dict[str, int | str] = {}
    for line in output.splitlines():
        match = re.match(r"^([^:]+):\s*(.+)$", line.strip())
        if not match:
            continue

        key = match.group(1).strip().lower().replace(" ", "_")
        value_text = match.group(2).strip()
        parsed[key] = int(value_text) if value_text.isdigit() else value_text
    return parsed


@mcp.tool("create_customer", description="Create a new customer")
async def create_customer_tool(
    first_name: Annotated[str, "Customer's first name"],
    last_name: Annotated[str, "Customer's last name"],
    date_of_birth: Annotated[str, "Customer's date of birth (YYYY-MM-DD)"],
    ssn: Annotated[str, "Social Security Number (XXX-XX-XXXX)"],
    gender: Annotated[str, "Customer's gender (Male, Female, Other, Prefer not to say)"],
) -> str:
    """
    Create a new customer in the system via FastAPI endpoint.

    This asynchronous tool creates a new customer record with provided personal information.
    It sends a POST request to the FastAPI backend and returns the response as a JSON string.

    Args:
        first_name: Customer's first name.
        last_name: Customer's last name.
        date_of_birth: Customer's date of birth in YYYY-MM-DD format.
        ssn: Social Security Number in XXX-XX-XXXX format.
        gender: Customer's gender. Accepted values: Male, Female, Other, Prefer not to say.

    Returns:
        str: JSON string containing the created customer details on success, or error details on failure.
            On success, returns the customer object from the API response.
            On HTTP errors, returns error with status code and response text.
            On other exceptions, returns error message with exception details.

    Raises:
        None: Exceptions are caught and returned as JSON error strings.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/customers",
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "date_of_birth": date_of_birth,
                    "ssn": ssn,
                    "gender": gender,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}", "details": e.response.text}, indent=2)
    except Exception as e:
        return json.dumps({"error": "Failed to create customer", "details": str(e)}, indent=2)


@mcp.tool("get_customer", description="Get customer details by ID")
async def get_customer_tool(customer_id: str) -> str:
    """
    Retrieve a customer by ID via FastAPI endpoint.

    This asynchronous tool fetches the details of a customer using their unique ID.
    It sends a GET request to the FastAPI backend and returns the response as a JSON string.

    Args:
        customer_id: The unique identifier of the customer.

    Returns:
        str: JSON string containing the customer details on success, or error details on failure.
            On success, returns the customer object from the API response.
            On HTTP errors, returns error with status code and response text.
            On other exceptions, returns error message with exception details.

    Raises:
        None: Exceptions are caught and returned as JSON error strings.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/api/v1/customers/{customer_id}",
                timeout=10.0,
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}", "details": e.response.text}, indent=2)
    except Exception as e:
        return json.dumps({"error": "Failed to get customer", "details": str(e)}, indent=2)


@mcp.tool("list_customers", description="List all customers")
async def list_customers_tool() -> str:
    """
    List all customers via FastAPI endpoint.

    This asynchronous tool fetches the details of all customers.
    It sends a GET request to the FastAPI backend and returns the response as a JSON string.

    Returns:
        str: JSON string containing the list of customers on success, or error details on failure.
            On success, returns the list of customer objects from the API response.
            On HTTP errors, returns error with status code and response text.
            On other exceptions, returns error message with exception details.

    Raises:
        None: Exceptions are caught and returned as JSON error strings.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/api/v1/customers",
                timeout=10.0,
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"HTTP {e.response.status_code}", "details": e.response.text}, indent=2)
    except Exception as e:
        return json.dumps({"error": "Failed to list customers", "details": str(e)}, indent=2)


@mcp.tool("create_savings_account", description="Create a new savings account for a customer")
async def create_savings_account_tool(
    customer_id: Annotated[str, "Customer's unique identifier"],
    initial_deposit: Annotated[float, "Initial deposit amount"] = 0,
) -> str:
    """
    Create a new savings account for a customer via FastAPI endpoint.

    This asynchronous tool creates a savings account for an existing customer.
    The customer ID is provided in the path. `initial_deposit` is accepted for
    compatibility with clients but is currently not required by the FastAPI endpoint.

    Args:
        customer_id: The unique identifier of the customer.
        initial_deposit: Initial deposit amount (currently ignored by API endpoint).

    Returns:
        str: JSON string containing the created account details on success, or error details on failure.
            On success, returns the account object from the API response.
            On HTTP errors, returns error with status code and response text.
            On other exceptions, returns error message with exception details.

        Raises:
            None: Exceptions are caught and returned as JSON error strings.
        """
    try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/api/v1/customers/{customer_id}/accounts",
                    timeout=10.0,
                )
                response.raise_for_status()
                return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}", "details": e.response.text}, indent=2)
    except Exception as e:
            return json.dumps({"error": "Failed to create savings account", "details": str(e)}, indent=2)


@mcp.tool("run_automation_maven_tests", description="Run Maven/TestNG automation test scripts to create Money Market Accounts for bank customers")
async def run_script_for_MMA(
    maven_goal: Annotated[str, "Maven goal to run: test or verify"] = "test",
    clean_first: Annotated[bool, "Run clean before the selected goal"] = False,
    testng_suite: Annotated[str, "Relative path to TestNG suite XML"] = "src/test/resources/testng.xml",
    cucumber_tags: Annotated[str, "Optional Cucumber tags expression (e.g. @login)"] = "",
    timeout_seconds: Annotated[int, "Command timeout in seconds"] = 900,
    max_output_chars: Annotated[int, "Max stdout/stderr chars to return"] = 8000,
    extra_properties: Annotated[str, "Optional JSON object of extra Maven -D properties, e.g. {\"customer.id\": \"cust_abc123\", \"account.type\": \"MMA\"}"] = "{}"
) -> str:
    """Execute Maven automation tests and return structured results."""
    if not AUTOMATION_MVN_TESTS_DIR.is_dir():
        return json.dumps(
            {
                "status": "error",
                "error": "automation_mvn_tests directory not found",
                "working_directory": AUTOMATION_MVN_TESTS_DIR.as_posix(),
            },
            indent=2,
        )

    goal = maven_goal.strip().lower()
    if goal not in ALLOWED_MAVEN_GOALS:
        return json.dumps(
            {
                "status": "error",
                "error": f"Unsupported maven_goal '{maven_goal}'. Allowed values: {sorted(ALLOWED_MAVEN_GOALS)}",
            },
            indent=2,
        )

    timeout_seconds = max(60, min(timeout_seconds, 3600))
    max_output_chars = max(1000, min(max_output_chars, 20000))

    try:
        suite_abs_path = _resolve_suite_path(testng_suite)
    except (ValueError, FileNotFoundError) as e:
        return json.dumps({"status": "error", "error": str(e)}, indent=2)

    maven_command = _find_maven_command()
    if not maven_command:
        return json.dumps(
            {
                "status": "error",
                "error": "Maven executable was not found. Install Maven or add mvnw to automation_mvn_tests.",
            },
            indent=2,
        )

    command = [*maven_command]
    if clean_first:
        command.append("clean")
    command.append(goal)

    suite_rel_path = suite_abs_path.relative_to(AUTOMATION_MVN_TESTS_DIR).as_posix()
    command.append(f"-Dsurefire.suiteXmlFiles={suite_rel_path}")

    if cucumber_tags.strip():
        command.append(f"-Dcucumber.filter.tags={cucumber_tags.strip()}")
    
        # Parse and append extra -D properties
    try:
        props: dict = json.loads(extra_properties) if extra_properties.strip() else {}
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "error": "extra_properties must be a valid JSON object string."}, indent=2)

    for key, value in props.items():
        command.append(f"-D{key}={value}")

    start = time.perf_counter()
    try:
        completed = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=str(AUTOMATION_MVN_TESTS_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        duration_seconds = round(time.perf_counter() - start, 2)

        return json.dumps(
            {
                "status": "success" if completed.returncode == 0 else "failed",
                "return_code": completed.returncode,
                "duration_seconds": duration_seconds,
                "working_directory": AUTOMATION_MVN_TESTS_DIR.as_posix(),
                "command": command,
                "reports": _collect_report_paths(),
                "stdout_tail": _tail_output(completed.stdout or "", max_output_chars),
                "stderr_tail": _tail_output(completed.stderr or "", max_output_chars),
            },
            indent=2,
        )
    except subprocess.TimeoutExpired as e:
        duration_seconds = round(time.perf_counter() - start, 2)
        return json.dumps(
            {
                "status": "timeout",
                "error": f"Maven command exceeded timeout of {timeout_seconds} seconds",
                "duration_seconds": duration_seconds,
                "working_directory": AUTOMATION_MVN_TESTS_DIR.as_posix(),
                "command": command,
                "stdout_tail": _tail_output(_normalize_stream(e.stdout), max_output_chars),
                "stderr_tail": _tail_output(_normalize_stream(e.stderr), max_output_chars),
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "error": "Failed to execute Maven automation tests",
                "details": str(e),
                "working_directory": AUTOMATION_MVN_TESTS_DIR.as_posix(),
            },
            indent=2,
        )


# @mcp.tool("run_xyz_bank_deposit", description="Run the XYZ Bank deposit script for performing deposit transactions to the savings account and return results")
# async def run_xyz_bank_deposit_tool(
#     headless: Annotated[bool, "Run the browser in headless mode"] = True,
#     timeout_seconds: Annotated[int, "Command timeout in seconds"] = 180,
#     max_output_chars: Annotated[int, "Max stdout/stderr chars to return"] = 8000,
# ) -> str:
#     """Execute the XYZ Bank Playwright deposit script and return structured results."""
#     xyz_bank_deposit_script = PROJECT_ROOT / "scripts" / "xyz_bank_deposit.py"
#     if not xyz_bank_deposit_script.is_file():
#         return json.dumps(
#             {
#                 "status": "error",
#                 "error": "xyz_bank_deposit.py script not found",
#                 "script_path": (PROJECT_ROOT / "scripts" / "xyz_bank_deposit.py").relative_to(PROJECT_ROOT).as_posix(),
#             },
#             indent=2,
#         )

#     requested_timeout_seconds = timeout_seconds
#     if timeout_seconds <= 0:
#         timeout_seconds = 30

#     timeout_seconds = max(0, min(timeout_seconds, 900))
#     max_output_chars = max(1000, min(max_output_chars, 20000))

#     env = os.environ.copy()
#     env["HEADLESS"] = "true" if headless else "false"
#     command = [sys.executable, "-u", str(xyz_bank_deposit_script)]

#     start = time.perf_counter()
#     try:
#         completed = await asyncio.to_thread(
#             subprocess.run,
#             command,
#             cwd=str(PROJECT_ROOT),
#             capture_output=True,
#             text=True,
#             timeout=timeout_seconds,
#             check=False,
#             env=env,
#         )
#         duration_seconds = round(time.perf_counter() - start, 2)
#         stdout = completed.stdout or ""
#         stderr = completed.stderr or ""

#         return json.dumps(
#             {
#                 "status": "success" if completed.returncode == 0 else "failed",
#                 "return_code": completed.returncode,
#                 "duration_seconds": duration_seconds,
#                 "script_path": xyz_bank_deposit_script.relative_to(PROJECT_ROOT).as_posix(),
#                 "headless": headless,
#                 "requested_timeout_seconds": requested_timeout_seconds,
#                 "effective_timeout_seconds": timeout_seconds,
#                 "result": _parse_script_output(stdout),
#                 "stdout_tail": _tail_output(stdout, max_output_chars),
#                 "stderr_tail": _tail_output(stderr, max_output_chars),
#             },
#             indent=2,
#         )
#     except subprocess.TimeoutExpired as e:
#         duration_seconds = round(time.perf_counter() - start, 2)
#         return json.dumps(
#             {
#                 "status": "timeout",
#                 "error": f"Deposit script exceeded timeout of {timeout_seconds} seconds",
#                 "duration_seconds": duration_seconds,
#                 "script_path": xyz_bank_deposit_script.relative_to(PROJECT_ROOT).as_posix(),
#                 "headless": headless,
#                 "requested_timeout_seconds": requested_timeout_seconds,
#                 "effective_timeout_seconds": timeout_seconds,
#                 "stdout_tail": _tail_output(_normalize_stream(e.stdout), max_output_chars),
#                 "stderr_tail": _tail_output(_normalize_stream(e.stderr), max_output_chars),
#             },
#             indent=2,
#         )
#     except Exception as e:
#         return json.dumps(
#             {
#                 "status": "error",
#                 "error": "Failed to execute XYZ Bank deposit script",
#                 "details": str(e),
#                 "script_path": xyz_bank_deposit_script.relative_to(PROJECT_ROOT).as_posix(),
#             },
#             indent=2,
#         )

def main():
    """Main function to start the MCP server."""
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()