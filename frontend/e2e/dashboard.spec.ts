import { test, expect } from "@playwright/test";
import { setLoggedIn, mockDashboardApi } from "./fixtures";

test.describe("Authenticated navigation", () => {
  test.beforeEach(async ({ page }) => {
    await setLoggedIn(page);
    await mockDashboardApi(page);
    // AlertFilters fetches sources — return an empty array so the component renders cleanly
    await page.route("**/api/v1/sources**", (route) => route.fulfill({ json: [] }));
    // Catch-all for any remaining API calls (must be registered last)
    await page.route("**/api/v1/**", (route) => route.fulfill({ json: {} }));
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
