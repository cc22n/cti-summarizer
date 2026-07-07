import { describe, it, expect } from "vitest";
import {
  transformTimeline,
  transformSeverityPie,
  transformSourceBar,
  SEVERITY_COLORS,
} from "./chartUtils";

describe("transformTimeline", () => {
  it("strips the year prefix from the date", () => {
    const result = transformTimeline([
      { date: "2026-06-15", count: 3, severity_breakdown: {} },
    ]);
    expect(result[0].date).toBe("06-15");
  });

  it("maps count to total", () => {
    const result = transformTimeline([
      { date: "2026-06-15", count: 7, severity_breakdown: {} },
    ]);
    expect(result[0].total).toBe(7);
  });

  it("fills missing severity keys with zero", () => {
    const result = transformTimeline([
      {
        date: "2026-06-15",
        count: 2,
        severity_breakdown: { critical: 2 },
      },
    ]);
    expect(result[0].high).toBe(0);
    expect(result[0].medium).toBe(0);
    expect(result[0].low).toBe(0);
    expect(result[0].info).toBe(0);
  });

  it("reads severity_breakdown values when present", () => {
    const result = transformTimeline([
      {
        date: "2026-06-15",
        count: 5,
        severity_breakdown: { critical: 3, high: 2 },
      },
    ]);
    expect(result[0].critical).toBe(3);
    expect(result[0].high).toBe(2);
  });

  it("returns an empty array for empty input", () => {
    expect(transformTimeline([])).toEqual([]);
  });
});

describe("transformSeverityPie", () => {
  it("filters out severity buckets with zero count", () => {
    const slices = transformSeverityPie({ critical: 5, high: 0, medium: 2 });
    const names = slices.map((s) => s.name);
    expect(names).not.toContain("high");
    expect(names).toContain("critical");
    expect(names).toContain("medium");
  });

  it("assigns the correct fill colour from SEVERITY_COLORS", () => {
    const slices = transformSeverityPie({ critical: 1 });
    expect(slices[0].fill).toBe(SEVERITY_COLORS["critical"]);
  });

  it("returns slices in canonical severity order", () => {
    const slices = transformSeverityPie({ info: 1, critical: 3, high: 2 });
    expect(slices[0].name).toBe("critical");
    expect(slices[1].name).toBe("high");
    expect(slices[2].name).toBe("info");
  });

  it("returns empty array when all counts are zero", () => {
    expect(transformSeverityPie({ critical: 0, high: 0 })).toEqual([]);
  });
});

describe("transformSourceBar", () => {
  it("sorts sources by count descending", () => {
    const bars = transformSourceBar({ NVD: 10, OTX: 50, CISA: 20 });
    expect(bars[0].source).toBe("OTX");
    expect(bars[1].source).toBe("CISA");
    expect(bars[2].source).toBe("NVD");
  });

  it("returns empty array for empty input", () => {
    expect(transformSourceBar({})).toEqual([]);
  });

  it("maps each source name and count correctly", () => {
    const bars = transformSourceBar({ NVD: 42 });
    expect(bars[0]).toEqual({ source: "NVD", count: 42 });
  });
});
