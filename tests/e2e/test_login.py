from playwright.sync_api import Page, expect


def test_valid_user_sees_welcome_back(page: Page, base_url: str):
    page.goto(f"{base_url}/login")

    page.get_by_label("Email").fill("test.user@example.com")
    page.get_by_label("Password").fill("Secure123")
    page.get_by_role("button", name="Log in").click()

    expect(page.get_by_text("Welcome back")).to_be_visible()
