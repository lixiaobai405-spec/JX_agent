import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.getenv("PDCA_API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
USERNAME = "demo_sales"
PASSWORD = "Demo@123456"


class SmokeError(RuntimeError):
    pass


def _request(method: str, path: str, token: str | None = None, data: dict | None = None, form: dict | None = None):
    url = f"{BASE_URL}{path}"
    headers = {}
    body = None

    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        body = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.URLError as exc:
        raise SmokeError(f"Request failed: {method} {url}: {exc}") from exc


def _assert(value, message: str) -> None:
    if not value:
        raise SmokeError(message)


def main() -> None:
    try:
        login = _request(
            "POST",
            "/auth/login",
            form={"username": USERNAME, "password": PASSWORD},
        )
        token = login["access_token"]

        me = _request("GET", "/auth/me", token=token)
        _assert(me["username"] == USERNAME, f"Unexpected user {me.get('username')}")

        period = _request("GET", "/periods/current", token=token)
        _assert(period and period["name"] == "2026年7月绩效演示周期", "Current demo period not found")

        goal = _request("GET", f"/do/goals/current?period_id={urllib.parse.quote(period['id'])}", token=token)
        _assert(goal and goal.get("id"), "Current goal not found")

        indicators = _request("GET", f"/do/goals/{goal['id']}/indicators", token=token)
        _assert(len(indicators) >= 5, f"Expected at least 5 indicators, got {len(indicators)}")

        diagnostic = _request("GET", f"/do/diagnostic-reports/goal/{goal['id']}/latest", token=token)
        _assert(diagnostic and diagnostic.get("improvement_suggestions"), "Latest diagnostic report not found")

        final_result = _request("GET", f"/check/final-results/goal/{goal['id']}", token=token)
        _assert(final_result and final_result.get("status") == "confirmed", "Confirmed final result not found")

        report = _request(
            "GET",
            f"/action/review-reports/user/{me['id']}/period/{period['id']}",
            token=token,
        )
        _assert(report and report.get("strengths_analysis"), "Review report not found")

        print(
            "PDCA_DEMO_FLOW "
            f"user={me['username']} "
            f"period={period['name']} "
            f"indicators={len(indicators)} "
            f"grade={final_result['final_grade']}"
        )
        print("PDCA_DEMO_FLOW_OK")
    except SmokeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
