// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SourcesPage from "./SourcesPage";
import { useSources } from "../hooks/useSources";

vi.mock("../hooks/useSources");
vi.mock("../components/layout/Header", () => ({
  default: ({ title }: any) => <h1>{title}</h1>,
}));
vi.mock("../components/sources/SourceCard", () => ({
  default: ({ source }: any) => <div data-testid="source-card">{source.name}</div>,
}));

const MOCK_SOURCES = [
  { id: 1, name: "NVD", source_type: "NVD", is_active: true, alert_count: 100, last_polled_at: null },
  { id: 2, name: "CISA KEV", source_type: "CISA_KEV", is_active: true, alert_count: 20, last_polled_at: null },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <SourcesPage />
    </MemoryRouter>
  );
}

describe("SourcesPage", () => {
  it("shows loading spinner while sources are fetching", () => {
    vi.mocked(useSources).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByText("Loading sources...")).toBeTruthy();
  });

  it("shows error message when sources fetch fails", () => {
    vi.mocked(useSources).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("connection refused"),
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("renders a card for each source when data loads", () => {
    vi.mocked(useSources).mockReturnValue({
      data: MOCK_SOURCES,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);
    renderPage();
    expect(screen.getByText("NVD")).toBeTruthy();
    expect(screen.getByText("CISA KEV")).toBeTruthy();
    expect(screen.getAllByTestId("source-card")).toHaveLength(2);
  });
});
