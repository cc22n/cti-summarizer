// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import AlertDetailPage from "./AlertDetailPage";
import { useAlert } from "../hooks/useAlerts";
import { useSummaries } from "../hooks/useSummaries";

vi.mock("../hooks/useAlerts");
vi.mock("../hooks/useSummaries");
vi.mock("../components/alerts/AlertDetailCard", () => ({ default: () => <div data-testid="alert-detail-card" /> }));
vi.mock("../components/summaries/SummaryCard", () => ({ default: () => <div data-testid="summary-card" /> }));

const MOCK_ALERT = { id: 42, title: "CVE-2026-1234", severity: "critical" };

function renderWithId(id = "42") {
  const router = createMemoryRouter(
    [{ path: "/alerts/:id", element: <AlertDetailPage /> }],
    { initialEntries: [`/alerts/${id}`] }
  );
  return render(<RouterProvider router={router} />);
}

describe("AlertDetailPage", () => {
  beforeEach(() => {
    vi.mocked(useSummaries).mockReturnValue({ data: undefined, isLoading: false } as any);
  });

  it("shows loading spinner while alert is fetching", () => {
    vi.mocked(useAlert).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderWithId();
    expect(screen.getByText("Loading alert...")).toBeTruthy();
  });

  it("shows error message when alert request fails", () => {
    vi.mocked(useAlert).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("not found"),
      refetch: vi.fn(),
    } as any);
    renderWithId();
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("shows Back to Alerts link when alert data is loaded", () => {
    vi.mocked(useAlert).mockReturnValue({
      data: MOCK_ALERT,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderWithId();
    expect(screen.getByText("Back to Alerts")).toBeTruthy();
  });
});
