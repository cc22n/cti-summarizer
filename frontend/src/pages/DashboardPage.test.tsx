// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DashboardPage from "./DashboardPage";
import { useDashboardOverview, useTimeline } from "../hooks/useDashboard";
import { useAlerts, useAlertStats } from "../hooks/useAlerts";

vi.mock("../hooks/useDashboard");
vi.mock("../hooks/useAlerts");
vi.mock("../components/layout/Header", () => ({
  default: ({ title, subtitle }: any) => (
    <div>
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
  ),
}));
vi.mock("../components/dashboard/OverviewCards", () => ({ default: () => <div data-testid="overview-cards" /> }));
vi.mock("../components/dashboard/TimelineChart", () => ({ default: () => <div data-testid="timeline-chart" /> }));
vi.mock("../components/dashboard/SeverityPieChart", () => ({ default: () => <div data-testid="severity-chart" /> }));
vi.mock("../components/dashboard/SourceBarChart", () => ({ default: () => <div data-testid="source-chart" /> }));
vi.mock("../components/dashboard/RecentAlertsTable", () => ({ default: () => <div data-testid="recent-alerts" /> }));

const OVERVIEW = {
  total_alerts: 50,
  alerts_24h: 5,
  critical_count: 2,
  high_count: 10,
  ingestion_sources: 3,
  last_ingested_at: null,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.mocked(useTimeline).mockReturnValue({ data: undefined, isLoading: false } as any);
    vi.mocked(useAlerts).mockReturnValue({ data: undefined, isLoading: false } as any);
    vi.mocked(useAlertStats).mockReturnValue({ data: undefined } as any);
  });

  it("shows animated skeleton while overview is loading", () => {
    vi.mocked(useDashboardOverview).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(document.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("shows error message when overview request fails", () => {
    vi.mocked(useDashboardOverview).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("network error"),
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("renders the Dashboard heading when data is available", () => {
    vi.mocked(useDashboardOverview).mockReturnValue({
      data: OVERVIEW,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy();
  });
});
