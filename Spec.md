# Spec: Login Demo

Local-only demo. Test credentials only.

## Backend (Flask, port 3000)
- `GET /login` serves the login page.
- `POST /api/login`, JSON body `{"email": str, "password": str}`
  - Valid user `test.user@example.com` / `Secure123` -> `200 {"message": "ok"}`
  - Missing/empty email (or password) -> `400 {"error": "..."}`
  - Wrong password / unknown user -> `401 {"error": "..."}`

## Frontend (`/login`)
- Labeled **Email** input, labeled **Password** input, **Log in** button.
- Success: show "Welcome back".
- Failure: show an error alert (`role="alert"`).

## E2E test (`tests/e2e/test_login.py`)
- Scenario: valid user logs in and sees "Welcome back".
- Locators: `get_by_label`, `get_by_role` only. No CSS selectors, no sleeps.
