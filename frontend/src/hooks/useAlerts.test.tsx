// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAlerts, useSemanticSearch } from "./useAlerts";
import { alertsApi } from "../services/alerts";

vi.mock("../services/alerts");
vi.mock("./useDebouncedValue", () => ({
  useDebouncedValue: (v: string) => v,
}));

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("useAlerts", () => {
  it("starts in pending state before the first fetch completes", () => {
    vi.mocked(alertsApi.list).mockResolvedValue({
      data: { items: [], total: 0, page: 1, pages: 1 },
    } as any);
    const { result } = renderHook(() => useAlerts({ page: 1 }), {
      wrapper: makeWrapper(),
    });
    expect(result.current.isPending).toBe(true);
  });
});

describe("useSemanticSearch", () => {
  it("is idle (disabled) when the query string is shorter than 3 characters", () => {
    const { result } = renderHook(() => useSemanticSearch("ab", 10), {
      wrapper: makeWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("is pending (enabled) when the query string is 3 or more characters", () => {
    vi.mocked(alertsApi.semanticSearch).mockResolvedValue({ data: [] } as any);
    const { result } = renderHook(() => useSemanticSearch("cve", 10), {
      wrapper: makeWrapper(),
    });
    expect(result.current.isPending).toBe(true);
  });
});
