import { test, expect } from "@playwright/test";

test.describe("404 page", () => {
  test("unknown route shows 404 text", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page.getByText("404")).toBeVisible();
  });

  test("shows a Back to Dashboard link", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page.getByRole("link", { name: "Back to Dashboard" })).toBeVisible();
  });

  test("Back to Dashboard link href points to /", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page.getByRole("link", { name: "Back to Dashboard" })).toHaveAttribute(
      "href",
      "/"
    );
  });
});
