// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SummariesPage from "./SummariesPage";
import { useLatestDigest, useSummaries, useGenerateDigest } from "../hooks/useSummaries";

vi.mock("../hooks/useSummaries");
vi.mock("../components/layout/Header", () => ({
  default: ({ title, actions }: any) => (
    <div>
      <h1>{title}</h1>
      {actions}
    </div>
  ),
}));
vi.mock("../components/summaries/DigestCard", () => ({ default: () => <div data-testid="digest-card" /> }));
vi.mock("../components/summaries/SummaryCard", () => ({ default: () => <div data-testid="summary-card" /> }));

const EMPTY_PAGE = { items: [], total: 0, page: 1, pages: 1 };

function renderPage() {
  return render(
    <MemoryRouter>
      <SummariesPage />
    </MemoryRouter>
  );
}

describe("SummariesPage", () => {
  beforeEach(() => {
    vi.mocked(useLatestDigest).mockReturnValue({ data: undefined, isLoading: false } as any);
    vi.mocked(useGenerateDigest).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);
  });

  it("shows loading spinner while summaries are fetching", () => {
    vi.mocked(useSummaries).mockReturnValue({ data: undefined, isLoading: true } as any);
    renderPage();
    expect(screen.getByText("Loading summaries...")).toBeTruthy();
  });

  it("shows empty state message when no summaries exist", () => {
    vi.mocked(useSummaries).mockReturnValue({ data: EMPTY_PAGE, isLoading: false } as any);
    renderPage();
    expect(screen.getByText("No summaries yet.")).toBeTruthy();
  });

  it("always renders the Generate Digest button", () => {
    vi.mocked(useSummaries).mockReturnValue({ data: undefined, isLoading: true } as any);
    renderPage();
    expect(screen.getByText("Generate Digest")).toBeTruthy();
  });
});
