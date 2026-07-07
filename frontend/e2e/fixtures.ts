import type { Page } from "@playwright/test";

export const MOCK_USER = { username: "admin", role: "admin" };

export const MOCK_OVERVIEW = {
  total_alerts: 42,
  alerts_24h: 5,
  critical_count: 2,
  high_count: 8,
  ingestion_sources: 5,
  last_ingested_at: "2026-06-22T12:00:00Z",
};

/** Mock the login endpoint so any credentials succeed. */
export async function mockLoginApi(page: Page) {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      json: { access_token: "test-jwt", ...MOCK_USER },
    })
  );
}

/** Mock the /auth/me endpoint so a stored token is accepted. */
export async function mockMeApi(page: Page) {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ json: MOCK_USER })
  );
}

/**
 * Inject a fake JWT into localStorage before the page loads and
 * intercept /auth/me so the app considers the user authenticated.
 * Call this in beforeEach before any page.goto().
 */
export async function setLoggedIn(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("cti_access_token", "test-jwt");
  });
  await mockMeApi(page);
}

/** Stub the main dashboard data endpoints so all charts render. */
export async function mockDashboardApi(page: Page) {
  await page.route("**/api/v1/dashboard/overview", (route) =>
    route.fulfill({ json: MOCK_OVERVIEW })
  );
  await page.route("**/api/v1/dashboard/timeline**", (route) =>
    route.fulfill({ json: { points: [] } })
  );
  await page.route("**/api/v1/alerts/stats", (route) =>
    route.fulfill({ json: { by_severity: {}, by_source: {} } })
  );
  await page.route("**/api/v1/alerts**", (route) =>
    route.fulfill({ json: { items: [], total: 0, page: 1, pages: 1 } })
  );
}
