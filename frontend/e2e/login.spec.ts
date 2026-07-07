import { test, expect } from "@playwright/test";
import { mockLoginApi, mockMeApi, setLoggedIn, mockDashboardApi } from "./fixtures";

test.describe("Login page", () => {
  test("visiting / while unauthenticated redirects to /login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("shows the CTI Summarizer heading", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "CTI Summarizer" })).toBeVisible();
  });

  test("shows username and password input fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
  });

  test("shows an error message when credentials are invalid", async ({ page }) => {
    await page.route("**/api/v1/auth/login", (route) =>
      route.fulfill({ status: 401, json: { detail: "Incorrect username or password" } })
    );
    await page.goto("/login");
    await page.getByLabel("Username").fill("wronguser");
    await page.getByLabel("Password").fill("wrongpass");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Invalid username or password")).toBeVisible();
  });

  test("redirects to / after a successful login", async ({ page }) => {
    await mockLoginApi(page);
    await mockMeApi(page);
    await mockDashboardApi(page);
    // Catch any remaining API calls so the dashboard renders without errors
    await page.route("**/api/v1/**", (route) => route.fulfill({ json: {} }));

    await page.goto("/login");
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("secret");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL("/");
  });
});
