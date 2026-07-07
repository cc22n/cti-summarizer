import { describe, it, expect } from "vitest";
import { formatDate, formatDateTime, formatRelativeTime, formatCVSS } from "./formatters";

describe("formatDate", () => {
  it("returns dash for null", () => {
    expect(formatDate(null)).toBe("—");
  });

  it("returns dash for undefined", () => {
    expect(formatDate(undefined)).toBe("—");
  });

  it("includes the year for a valid ISO date", () => {
    const result = formatDate("2026-03-15T00:00:00Z");
    expect(result).toContain("2026");
  });

  it("includes the abbreviated month for a valid ISO date", () => {
    // Use noon UTC on the 15th so no timezone shift changes the month
    const result = formatDate("2026-06-15T12:00:00Z");
    expect(result).toContain("Jun");
  });
});

describe("formatDateTime", () => {
  it("returns dash for null", () => {
    expect(formatDateTime(null)).toBe("—");
  });

  it("returns dash for undefined", () => {
    expect(formatDateTime(undefined)).toBe("—");
  });

  it("includes year and month for a valid timestamp", () => {
    const result = formatDateTime("2026-03-15T12:30:00Z");
    expect(result).toContain("2026");
  });
});

describe("formatRelativeTime", () => {
  it("returns never for null", () => {
    expect(formatRelativeTime(null)).toBe("never");
  });

  it("returns never for undefined", () => {
    expect(formatRelativeTime(undefined)).toBe("never");
  });

  it("returns just now for a timestamp less than 1 minute ago", () => {
    const recent = new Date(Date.now() - 10_000).toISOString();
    expect(formatRelativeTime(recent)).toBe("just now");
  });

  it("returns minutes ago for a timestamp under an hour", () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60_000).toISOString();
    expect(formatRelativeTime(fiveMinAgo)).toBe("5m ago");
  });

  it("returns hours ago for a timestamp under 24 hours", () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60_000).toISOString();
    expect(formatRelativeTime(twoHoursAgo)).toBe("2h ago");
  });

  it("returns days ago for an old timestamp", () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60_000).toISOString();
    expect(formatRelativeTime(threeDaysAgo)).toBe("3d ago");
  });
});

describe("formatCVSS", () => {
  it("returns N/A for null", () => {
    expect(formatCVSS(null)).toBe("N/A");
  });

  it("returns N/A for undefined", () => {
    expect(formatCVSS(undefined)).toBe("N/A");
  });

  it("formats a decimal string to one decimal place", () => {
    expect(formatCVSS("7.5")).toBe("7.5");
  });

  it("appends .0 to an integer string", () => {
    expect(formatCVSS("9")).toBe("9.0");
  });

  it("rounds to one decimal place", () => {
    expect(formatCVSS("8.56")).toBe("8.6");
  });
});
