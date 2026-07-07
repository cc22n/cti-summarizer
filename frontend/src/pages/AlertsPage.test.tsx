// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AlertsPage from "./AlertsPage";
import { useAlerts } from "../hooks/useAlerts";

vi.mock("../hooks/useAlerts");
vi.mock("../components/layout/Header", () => ({
  default: ({ title, subtitle, actions }: any) => (
    <div>
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
      {actions}
    </div>
  ),
}));
vi.mock("../components/alerts/AlertTable", () => ({ default: () => <div data-testid="alert-table" /> }));
vi.mock("../components/alerts/AlertFilters", () => ({ default: () => <div data-testid="alert-filters" /> }));

function renderPage() {
  return render(
    <MemoryRouter>
      <AlertsPage />
    </MemoryRouter>
  );
}

describe("AlertsPage", () => {
  it("renders the Alerts heading regardless of load state", () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByRole("heading", { name: "Alerts" })).toBeTruthy();
  });

  it("shows error component and retry button when fetch fails", () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("fetch failed"),
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("shows total alert count in subtitle when data loads", () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: { items: [], total: 87, page: 1, pages: 1 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByText(/total alerts/)).toBeTruthy();
  });
});
