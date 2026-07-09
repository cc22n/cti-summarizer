import { test, expect } from "@playwright/test";
import { setLoggedIn, mockAppApi } from "./fixtures";

/** Build a full Alert payload matching types/alert.ts. */
function makeAlert(id: number, title: string, severity: string, acked = false) {
  return {
    id,
    raw_alert_id: id,
    title,
    description: `Description for ${title}`,
    severity,
    cvss_score: "7.50",
    source_name: "NVD",
    affected_products: null,
    attack_vectors: null,
    mitre_techniques: null,
    iocs: null,
    published_date: "2026-06-20T10:00:00Z",
    normalized_at: "2026-06-20T11:00:00Z",
    categories: [],
    notes: null,
    is_acknowledged: acked,
    acknowledged_at: acked ? "2026-06-22T09:00:00Z" : null,
  };
}

function listResponse(items: unknown[], total?: number, page = 1, pages = 1) {
  return { items, total: total ?? items.length, page, page_size: 20, pages };
}

test.describe("Alerts flows", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/**", (route) => route.fulfill({ json: {} }));
    await mockAppApi(page);
    await setLoggedIn(page);
  });

  test("selecting a severity narrows the table via refetch", async ({ page }) => {
    const critical = makeAlert(1, "CRIT-ONLY-ALERT", "critical");
    const low = makeAlert(2, "LOW-ONLY-ALERT", "low");

    // Registered after mockAppApi's broad alerts** mock, so it wins for
    // the list endpoint (query string present) but not for /alerts/{id}.
    await page.route("**/api/v1/alerts?**", (route) => {
      const url = new URL(route.request().url());
      const severity = url.searchParams.get("severity");
      const items = severity === "critical" ? [critical] : [critical, low];
      return route.fulfill({ json: listResponse(items) });
    });

    await page.goto("/alerts");
    await expect(page.getByRole("link", { name: /LOW-ONLY-ALERT/ })).toBeVisible();

    // Severity is the first combobox (search box is a textbox).
    await page.getByRole("combobox").first().selectOption("critical");

    await expect(page.getByRole("link", { name: /LOW-ONLY-ALERT/ })).toBeHidden();
    await expect(page.getByRole("link", { name: /CRIT-ONLY-ALERT/ })).toBeVisible();
  });

  test("pagination loads the next page of alerts", async ({ page }) => {
    await page.route("**/api/v1/alerts?**", (route) => {
      const url = new URL(route.request().url());
      const pageNum = Number(url.searchParams.get("page") ?? "1");
      const items =
        pageNum === 2
          ? [makeAlert(21, "PAGE2-ALERT", "medium")]
          : [makeAlert(1, "PAGE1-ALERT", "high")];
      return route.fulfill({ json: listResponse(items, 40, pageNum, 2) });
    });

    await page.goto("/alerts");
    await expect(page.getByRole("link", { name: /PAGE1-ALERT/ })).toBeVisible();

    await page.getByRole("button", { name: "Next page" }).click();

    await expect(page.getByRole("link", { name: /PAGE2-ALERT/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /PAGE1-ALERT/ })).toBeHidden();
  });

  test("acknowledging an alert flips the button state", async ({ page }) => {
    // Stateful mock: after the PATCH, the detail refetch returns acked=true.
    let acked = false;
    await page.route("**/api/v1/alerts/42", (route) =>
      route.fulfill({ json: makeAlert(42, "ACK-FLOW-ALERT", "high", acked) })
    );
    await page.route("**/api/v1/alerts/42/acknowledge", (route) => {
      acked = true;
      return route.fulfill({ json: makeAlert(42, "ACK-FLOW-ALERT", "high", true) });
    });

    await page.goto("/alerts/42");
    await page.getByRole("button", { name: "Acknowledge", exact: true }).click();
    await expect(page.getByRole("button", { name: "Acknowledged" })).toBeVisible();
  });

  test("a page render crash shows the friendly fallback, not the router error screen", async ({ page }) => {
    // {} is missing .series, which makes PredictionsPage throw during render.
    await page.route("**/api/v1/predictions/latest", (route) =>
      route.fulfill({ json: {} })
    );

    await page.goto("/predictions");

    await expect(
      page.getByText("Something went wrong rendering this page.")
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Unexpected Application Error!" })
    ).toBeHidden();
  });
});
