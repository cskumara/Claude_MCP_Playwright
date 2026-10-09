# Playwright End-to-End Testing, Step by Step: Write the Test, Reproduce the Failure, Debug It and Fix It (with Claude Code + Playwright MCP)

> **Posting to Medium:** Medium doesn't render Markdown tables, so every table here is an image (`screenshots/04-evidence-table.png` and `screenshots/05-before-after-table.png`). Upload each image where you see an `[IMAGE: ...]` line. Code blocks paste fine into Medium (type three backticks).

---

A failing test tells you *that* something is broken. It rarely tells you *why*.

In this guide I build a small login app, add a Playwright end-to-end test to it, watch the test fail, and then debug the failure two ways: with Playwright's own tools (traces, screenshots, the inspector) and with **Claude Code driving a real browser through the Playwright MCP server**. Then I fix the bug and prove the fix.

Every command and output below comes from a real run on my machine. Everything is local, with test credentials only.

**What you'll learn**
- How to set up Playwright with pytest in a Python project
- How to write a clean E2E test with good locators
- How to read a Playwright failure (it's more helpful than you'd think)
- How to debug with screenshots, traces, headed mode and the inspector
- How to debug with Playwright MCP and Claude Code
- How to fix the bug, verify it, and write more tests so it stays fixed

## The project

A tiny login demo:

- **Backend:** Flask on port 3000
  - `GET /login` serves the page
  - `POST /api/login` takes JSON `{"email": "...", "password": "..."}`
    - Valid user returns `200 {"message": "ok"}`
    - Missing email or password returns `400 {"error": "..."}`
    - Wrong password or unknown user returns `401 {"error": "..."}`
- **Frontend:** one HTML page with a labeled **Email** input, a labeled **Password** input and a **Log in** button. On success it shows "Welcome back". On failure it shows an error alert (`role="alert"`).
- **Test:** one Playwright test that logs in as a valid user and expects "Welcome back"

The only valid user is `test.user@example.com` with password `Secure123`.

Project layout:

```
app/
  server.py             Flask app (port 3000)
  templates/login.html  Login page
  static/login.js       Form submit logic
tests/e2e/
  conftest.py           Starts the Flask server for the tests
  test_login.py         The Playwright test
screenshots/            Browser evidence
pytest.ini
requirements.txt
.mcp.json               Playwright MCP config
CLAUDE.md               Project rules for Claude Code
Spec.md                 The specification
```

---

# Part 1: Implement Playwright in your project

## Step 1: Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

`requirements.txt` has three packages:

```
flask
pytest
pytest-playwright
```

`pytest-playwright` is the plugin that gives pytest the `page` fixture, a fresh browser page for every test. `playwright install chromium` downloads the browser Playwright controls.

## Step 2: Configure pytest

`pytest.ini`:

```ini
[pytest]
testpaths = tests
```

That's all you need. pytest will look in `tests/` for tests.

## Step 3: Start the app automatically for tests

A good E2E setup starts the app itself, so one command runs everything. `tests/e2e/conftest.py`:

```python
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:3000"


@pytest.fixture(scope="session", autouse=True)
def server():
    proc = subprocess.Popen([sys.executable, str(ROOT / "app" / "server.py")])
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE_URL}/login")
            break
        except OSError:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("Flask server did not start")
    yield
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL
```

What this does:
- `scope="session", autouse=True` starts the server once, before any test, with no need to ask for it.
- The loop polls `/login` until the server answers. It waits for the server to be ready, so there's no blind `sleep`.
- After `yield`, it shuts the server down when the tests finish.
- `base_url` gives tests the address, so no test hard-codes a URL.

## Step 4: Write the first test

`tests/e2e/test_login.py`:

```python
from playwright.sync_api import Page, expect


def test_valid_user_sees_welcome_back(page: Page, base_url: str):
    page.goto(f"{base_url}/login")

    page.get_by_label("Email").fill("test.user@example.com")
    page.get_by_label("Password").fill("Secure123")
    page.get_by_role("button", name="Log in").click()

    expect(page.get_by_text("Welcome back")).to_be_visible()
```

Three habits in this small test are worth copying:

1. **Locate elements the way a user sees them.** `get_by_label("Email")` and `get_by_role("button", name="Log in")` find elements by their accessible label and role. No CSS selectors, so a styling change won't break the test, and the test also proves the form is properly labeled.
2. **Use `expect`, not `assert`, for the page.** `expect(...).to_be_visible()` retries until the element appears or a timeout (5 seconds by default) runs out. That's why there are no `sleep` calls: the login request is asynchronous, and Playwright simply waits.
3. **One scenario per test.** The name says what's expected.

## Step 5: Run it

```bash
.venv/bin/pytest -v
```

---

# Part 2: The test fails. Now what?

My first run did not pass. Here's the real output:

```
tests/e2e/test_login.py::test_valid_user_sees_welcome_back[chromium] FAILED [100%]

=================================== FAILURES ===================================
_________________ test_valid_user_sees_welcome_back[chromium] __________________

page = <Page url='http://127.0.0.1:3000/login'>
base_url = 'http://127.0.0.1:3000'

    def test_valid_user_sees_welcome_back(page: Page, base_url: str):
        page.goto(f"{base_url}/login")

        page.get_by_label("Email").fill("test.user@example.com")
        page.get_by_label("Password").fill("Secure123")
        page.get_by_role("button", name="Log in").click()

>       expect(page.get_by_text("Welcome back")).to_be_visible()
E       AssertionError: Locator expected to be visible
E       Actual value: None
E       Error: element(s) not found
E       Call log:
E         - Expect "to_be_visible" get_by_text("Welcome back") with timeout 5000ms
E         - waiting for get_by_text("Welcome back")
E
E       Aria snapshot:
E       - main:
E         - heading "Sign in" [level=1]
E         - text: Email
E         - textbox "Email": test.user@example.com
E         - text: Password
E         - textbox "Password": Secure123
E         - button "Log in"
E         - alert: Email is required

tests/e2e/test_login.py:11: AssertionError
...
127.0.0.1 - - "GET /login HTTP/1.1" 200 -
127.0.0.1 - - "GET /static/login.js HTTP/1.1" 200 -
127.0.0.1 - - "POST /api/login HTTP/1.1" 400 -
============================== 1 failed in 7.00s ===============================
```

## How to read this failure

Don't skim it. Playwright packs a lot of debugging information into this output:

- **`>` marks the line that failed:** the `expect(... "Welcome back" ...)` on line 11.
- **`Call log`** shows Playwright waited the full 5000 ms for "Welcome back" and never saw it. So it's not a timing problem.
- **`Aria snapshot`** is the page as the browser's accessibility tree saw it at the moment of failure. Both fields are filled in correctly, and there's an unexpected extra line: **`alert: Email is required`**.
- **The server log** shows `POST /api/login ... 400`. The server rejected the login.

That's already a strong clue: the email *was* typed in, yet the server says it's missing.

Playwright also saved a screenshot of the page at the moment of failure:

[IMAGE: screenshots/06-pytest-failure-screenshot.png]

## Debugging tools built into Playwright

Before reaching for anything fancy, these four options cover most cases.

**1. Screenshot on failure**

```bash
.venv/bin/pytest --screenshot only-on-failure --output test-results
```

This is how I got the image above. Files go to `test-results/`.

**2. Trace everything**

```bash
.venv/bin/pytest --tracing on --output test-results
.venv/bin/playwright show-trace test-results/<test-folder>/trace.zip
```

A trace is a recording of the test. The Trace Viewer lets you scrub through each action, see a DOM snapshot before and after it, and open the **Network** and **Console** tabs. Use `--tracing retain-on-failure` in CI to keep traces only for failed tests.

**3. Watch it run**

```bash
.venv/bin/pytest --headed --slowmo 500
```

`--headed` opens a visible browser and `--slowmo 500` pauses 500 ms between actions, so you can follow along.

**4. Step through with the Playwright Inspector**

```bash
PWDEBUG=1 .venv/bin/pytest tests/e2e/test_login.py
```

This opens the Inspector, where you can step through actions one at a time and test locators live. You can also drop `page.pause()` into a test to stop at a specific line.

Bonus: `playwright codegen http://localhost:3000/login` records your clicks in a browser and writes the test code for you. It's a good way to find the right locators.

---

# Part 3: Debug with Playwright MCP and Claude Code

The tools above are great when you drive. **Playwright MCP** lets Claude Code drive the browser for you: navigate, click, fill forms, take screenshots, read console messages and inspect network requests, all through tool calls, with no test script needed.

## Step 6: Connect Playwright MCP to Claude Code

Add `.mcp.json` to the project root:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

It needs Node.js for `npx`. Then run `/mcp` inside Claude Code to confirm the `playwright` server is connected. I told Claude Code to check the browser tools were available and to **stop** if they weren't, rather than quietly substituting another tool.

## Step 7: Give Claude Code ground rules

I keep a `CLAUDE.md` in the project:

```
- Local environment and test credentials only.
- Never edit or delete a test just to make it pass.
- Tests use get_by_label / get_by_role; no CSS selectors, no sleeps.
- Smallest fix in the right place. If stuck after 3 attempts, stop and report.
- Commit messages explain the root cause.
```

The second rule is the important one. The test describes the behavior we want, so a failing test means the *code* has to change, not the test.

I also told Claude Code: **do not change any code until I say so.** Reproduce first.

## Step 8: Reproduce the bug in a real browser

Start the app:

```bash
.venv/bin/python app/server.py
```

Then Claude Code, through Playwright MCP:

1. Opened `http://localhost:3000/login`
2. Took a screenshot
3. Filled Email = `test.user@example.com` and Password = `Secure123`
4. Clicked **Log in**
5. Took a second screenshot
6. Read the page snapshot, the console messages and the network requests

**The login page before submitting:**

[IMAGE: screenshots/01-login-page.png]

**After clicking "Log in":**

[IMAGE: screenshots/02-failure.png]

The bug reproduces by hand, so it's a real app bug, not a flaky test.

## Step 9: Read the evidence before changing anything

The screenshot shows *what* happened. The network request shows *why*.

The console had two errors. One was a harmless `404` on `/favicon.ico`. The other was a `400 BAD REQUEST` on `POST /api/login`. There were no JavaScript exceptions.

The network list:

```
1. [GET]  http://localhost:3000/login            => [200] OK
2. [GET]  http://localhost:3000/static/login.js  => [200] OK
3. [POST] http://localhost:3000/api/login        => [400] BAD REQUEST
```

The full request body of call #3:

```json
{"username":"test.user@example.com","password":"Secure123"}
```

And the response:

```json
{"error":"Email is required"}
```

Everything captured, in one place:

[IMAGE: screenshots/04-evidence-table.png]

Look at the request body. The form field is labeled **Email**, but the JSON key is `username`. The server wants `email`, finds nothing, and correctly says the email is missing. The alert text was misleading. The network tab told the truth.

## Step 10: Confirm the root cause in the source

Only now did Claude Code open the code.

`app/static/login.js` builds the request:

```javascript
body: JSON.stringify({
  username: form.elements.email.value,   // <-- wrong key
  password: form.elements.password.value,
}),
```

`app/server.py` reads it:

```python
data = request.get_json(silent=True) or {}
email = data.get("email")
password = data.get("password")
if not email:
    return jsonify(error="Email is required"), 400
```

The spec says the API takes `{"email", "password"}`. The server matches the spec and the frontend doesn't.

**Root cause:** `login.js` sends the email under `username`, but the API expects `email`.

---

# Part 4: Fix and verify

## Step 11: Apply the smallest fix

```diff
-      username: form.elements.email.value,
+      email: form.elements.email.value,
```

One line, in the right place. I didn't change the server, because it already matched the spec, and I didn't touch the test, because it was right.

## Step 12: Verify with the test, unchanged

```bash
.venv/bin/pytest -v
```

```
tests/e2e/test_login.py::test_valid_user_sees_welcome_back[chromium] PASSED [100%]

============================== 1 passed in 1.92s ===============================
```

## Step 13: Verify by hand in the browser

Same steps as Step 8. This time `POST /api/login` returned `200 OK` and the page showed **"Welcome back"**:

[IMAGE: screenshots/03-success.png]

Before and after, side by side:

[IMAGE: screenshots/05-before-after-table.png]

## Step 14: Commit with the root cause

A good commit message says *why* the bug happened, not just what changed:

```
Fix login: send "email" instead of "username" in request body

login.js posted {"username": ...} but POST /api/login (per spec) reads
"email", so every valid login got 400 "Email is required". Rename the
payload key to match the API contract.
```

---

# Part 5: Make sure it stays fixed

One passing test is a start. Here are four more, and I ran all of them against the fixed app (4 passed in 2.11 s). Add them to `tests/e2e/test_login_extra.py`:

```python
import json

from playwright.sync_api import Page, expect


def login(page: Page, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Log in").click()


def test_wrong_password_shows_error(page: Page, base_url: str):
    login(page, base_url, "test.user@example.com", "WrongPass1")

    expect(page.get_by_role("alert")).to_have_text("Invalid email or password")
    expect(page.get_by_text("Welcome back")).to_have_count(0)


def test_empty_email_shows_error(page: Page, base_url: str):
    login(page, base_url, "", "Secure123")

    expect(page.get_by_role("alert")).to_have_text("Email is required")


def test_login_request_uses_email_key(page: Page, base_url: str):
    page.goto(f"{base_url}/login")
    page.get_by_label("Email").fill("test.user@example.com")
    page.get_by_label("Password").fill("Secure123")

    with page.expect_request("**/api/login") as req_info:
        page.get_by_role("button", name="Log in").click()

    body = json.loads(req_info.value.post_data)
    assert body == {"email": "test.user@example.com", "password": "Secure123"}
    assert req_info.value.response().status == 200


def test_no_console_errors_on_login(page: Page, base_url: str):
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    login(page, base_url, "test.user@example.com", "Secure123")
    expect(page.get_by_text("Welcome back")).to_be_visible()

    assert [e for e in errors if "favicon" not in e] == []
```

Output:

```
test_login_extra.py::test_wrong_password_shows_error[chromium] PASSED     [ 25%]
test_login_extra.py::test_empty_email_shows_error[chromium] PASSED        [ 50%]
test_login_extra.py::test_login_request_uses_email_key[chromium] PASSED   [ 75%]
test_login_extra.py::test_no_console_errors_on_login[chromium] PASSED     [100%]

============================== 4 passed in 2.11s ===============================
```

What each one teaches:

- **A shared `login()` helper** removes repeated steps. Keep it plain; avoid clever abstractions in tests.
- **`test_wrong_password_shows_error`** tests the failure path, not just the happy path. `to_have_count(0)` asserts something is *absent*.
- **`test_empty_email_shows_error`** is the "Email is required" message again, now tested on purpose.
- **`test_login_request_uses_email_key`** is a regression test for exactly this bug. `page.expect_request(...)` captures the real network request, so the test checks the JSON key sent to the server. If someone changes `email` back to `username`, this fails right away with a clear message.
- **`test_no_console_errors_on_login`** listens with `page.on("console", ...)` and fails on unexpected console errors. It ignores the known harmless favicon 404.

## Why did the first test catch the bug but not explain it?

An E2E test checks the *outcome* ("Welcome back" appears). It can't tell you which layer broke. That's the reason to learn the debugging tools: a screenshot, a trace and the network tab turn "it failed" into "the client sent the wrong key".

---

## Quick reference: Playwright for Python

**Locators (prefer these):**

```python
page.get_by_role("button", name="Log in")
page.get_by_label("Email")
page.get_by_text("Welcome back")
page.get_by_placeholder("Search")
page.get_by_test_id("submit")      # needs a data-testid attribute
```

**Actions:**

```python
locator.fill("text")        # type into an input
locator.click()
locator.press("Enter")
locator.select_option("uk")
locator.check()
```

**Assertions (auto-retrying):**

```python
expect(locator).to_be_visible()
expect(locator).to_have_text("Welcome back")
expect(locator).to_have_count(0)
expect(page).to_have_url(re.compile(r"/dashboard"))
```

**Debug flags:**

```bash
pytest --headed --slowmo 500
pytest --screenshot only-on-failure
pytest --tracing retain-on-failure
pytest --video retain-on-failure
PWDEBUG=1 pytest
playwright show-trace trace.zip
playwright codegen http://localhost:3000/login
```

## What I'd take away from this

1. **Use real, user-facing locators.** `get_by_label` and `get_by_role` make tests stable and check accessibility for free.
2. **Never use `sleep`.** `expect` waits for you.
3. **Read the failure output.** The call log, the aria snapshot and the server log already pointed at the answer.
4. **Reproduce before you fix.** Seeing the failure in a real browser gave me evidence, not a guess.
5. **The network tab beats the screenshot.** The alert said "Email is required", which was misleading. The request body showed the real problem.
6. **Don't edit the test to make it pass.** The test described the desired behavior, so I changed the code.
7. **Keep the fix small, then add a regression test** that would have caught the bug.
8. **Verify twice.** An automated test and a manual run each confirm the fix.

## Try it yourself

The full project is on GitHub: `<your-repo-link>`

Clone it, follow Part 1, and the README covers running the app and the tests. To practice the debugging loop, reintroduce the bug by changing `email:` back to `username:` in `app/static/login.js`, then follow Parts 2 and 3.

---

*Tags to use on Medium: Playwright, Python, End-to-End Testing, Claude Code, MCP, Debugging*
