// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PredictionsPage from "./PredictionsPage";
import { useLatestPredictions, useGeneratePredictions } from "../hooks/usePredictions";
import { useTimeline } from "../hooks/useDashboard";

vi.mock("../hooks/usePredictions");
vi.mock("../hooks/useDashboard");
vi.mock("../components/layout/Header", () => ({
  default: ({ title }: any) => <h1>{title}</h1>,
}));
vi.mock("../components/predictions/PredictionChart", () => ({
  default: () => <div data-testid="prediction-chart" />,
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <PredictionsPage />
    </MemoryRouter>
  );
}

describe("PredictionsPage", () => {
  beforeEach(() => {
    vi.mocked(useTimeline).mockReturnValue({ data: undefined, isLoading: false } as any);
    vi.mocked(useGeneratePredictions).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isSuccess: false,
    } as any);
  });

  it("shows loading spinner while predictions are fetching", () => {
    vi.mocked(useLatestPredictions).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);
    renderPage();
    expect(screen.getByText("Loading predictions...")).toBeTruthy();
  });

  it("shows no-predictions message when there is an error and no data", () => {
    vi.mocked(useLatestPredictions).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("404 no predictions"),
    } as any);
    renderPage();
    expect(screen.getByText("No predictions available yet.")).toBeTruthy();
  });

  it("always renders the Regenerate button", () => {
    vi.mocked(useLatestPredictions).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);
    renderPage();
    expect(screen.getByText("Regenerate")).toBeTruthy();
  });
});
