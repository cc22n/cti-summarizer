import { test, expect } from "@playwright/test";
import { setLoggedIn, mockAppApi } from "./fixtures";

test.describe("Authenticated navigation", () => {
  test.beforeEach(async ({ page }) => {
    // Catch-all registered FIRST = lowest priority in Playwright (last added wins).
    // mockAppApi registers correctly shaped responses for every endpoint the
    // pages dereference; a bare {} fallback makes pages crash before rendering.
    await page.route("**/api/v1/**", (route) => route.fulfill({ json: {} }));
    await mockAppApi(page);
    await setLoggedIn(page);
  });

  test("authenticated user sees the Dashboard heading at /", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("/alerts shows the Alerts heading", async ({ page }) => {
    await page.goto("/alerts");
    await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
  });

  test("/sources shows the Sources heading", async ({ page }) => {
    await page.goto("/sources");
    await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  });

  test("/summaries shows the Summaries heading", async ({ page }) => {
    await page.goto("/summaries");
    await expect(page.getByRole("heading", { name: "Summaries" })).toBeVisible();
  });

  test("/predictions shows the Predictions heading", async ({ page }) => {
    await page.goto("/predictions");
    await expect(page.getByRole("heading", { name: "Predictions" })).toBeVisible();
  });
});
