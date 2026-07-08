import type { Page } from "@playwright/test";

export const MOCK_USER = { username: "admin", role: "admin" };

// Shape must match types/dashboard.ts DashboardOverview exactly:
// OverviewCards calls .toLocaleString() on these fields and crashes on undefined.
export const MOCK_OVERVIEW = {
  total_alerts: 42,
  alerts_today: 5,
  alerts_this_week: 18,
  critical_count: 2,
  high_count: 8,
  sources_active: 5,
  sources_total: 7,
  last_ingestion: "2026-06-22T12:00:00Z",
};

export const MOCK_STATS = {
  total_alerts: 42,
  by_severity: { critical: 2, high: 8, medium: 20, low: 7, info: 5 },
  by_source: { NVD: 25, CISA_KEV: 10, OTX: 7 },
  last_24h: 5,
  last_7d: 18,
};

export const MOCK_DIGEST = {
  id: 1,
  normalized_alert_id: null,
  summary_type: "digest",
  content: "## Test digest\nNo notable activity.",
  model_used: "grok-4-1-fast",
  prompt_tokens: 100,
  completion_tokens: 50,
  period_start: "2026-06-21T00:00:00Z",
  period_end: "2026-06-22T00:00:00Z",
  created_at: "2026-06-22T08:00:00Z",
};

export const MOCK_SUMMARIES_LIST = {
  items: [MOCK_DIGEST],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
};

export const MOCK_PREDICTIONS = {
  run_id: "test-run-1",
  generated_at: "2026-06-22T03:00:00Z",
  training_days: 90,
  model_type: "prophet",
  series: {
    total: [
      { date: "2026-06-23", predicted: 10, lower: 5, upper: 15, is_anomaly: false },
    ],
    critical: [
      { date: "2026-06-23", predicted: 1, lower: 0, upper: 3, is_anomaly: false },
    ],
  },
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

/**
 * Stub every endpoint the authenticated pages query, with correctly
 * shaped payloads. A `{}` fallback is NOT enough: pages dereference
 * fields (data.items.length, predictions.series, stats.by_severity)
 * and crash into the router error screen, so headings never render.
 *
 * Playwright gives priority to the LAST registered route, so broader
 * patterns are registered first and more specific ones after (e.g.
 * alerts** before alerts/stats, summaries** before digest/latest).
 */
export async function mockAppApi(page: Page) {
  await page.route("**/api/v1/sources**", (route) =>
    route.fulfill({ json: [] })
  );
  await page.route("**/api/v1/dashboard/overview", (route) =>
    route.fulfill({ json: MOCK_OVERVIEW })
  );
  await page.route("**/api/v1/dashboard/timeline**", (route) =>
    route.fulfill({ json: { points: [], period: "30d" } })
  );
  await page.route("**/api/v1/alerts**", (route) =>
    route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 20, pages: 1 } })
  );
  await page.route("**/api/v1/alerts/stats", (route) =>
    route.fulfill({ json: MOCK_STATS })
  );
  await page.route("**/api/v1/summaries**", (route) =>
    route.fulfill({ json: MOCK_SUMMARIES_LIST })
  );
  await page.route("**/api/v1/summaries/digest/latest", (route) =>
    route.fulfill({ json: MOCK_DIGEST })
  );
  await page.route("**/api/v1/predictions/latest", (route) =>
    route.fulfill({ json: MOCK_PREDICTIONS })
  );
  await page.route("**/api/v1/categories**", (route) =>
    route.fulfill({ json: [] })
  );
}

/** @deprecated kept for older specs; prefer mockAppApi. */
export async function mockDashboardApi(page: Page) {
  await mockAppApi(page);
}
