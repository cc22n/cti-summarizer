// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SeverityBadge from "./SeverityBadge";

describe("SeverityBadge", () => {
  it("renders the severity label text", () => {
    render(<SeverityBadge severity="critical" />);
    expect(screen.getByText("critical")).toBeTruthy();
  });

  it("applies the red color class for critical severity", () => {
    const { container } = render(<SeverityBadge severity="critical" />);
    expect(container.firstElementChild?.className).toContain("red");
  });

  it("applies the orange color class for high severity", () => {
    const { container } = render(<SeverityBadge severity="high" />);
    expect(container.firstElementChild?.className).toContain("orange");
  });

  it("applies the yellow color class for medium severity", () => {
    const { container } = render(<SeverityBadge severity="medium" />);
    expect(container.firstElementChild?.className).toContain("yellow");
  });

  it("falls back to the info style for an unknown severity", () => {
    const { container } = render(<SeverityBadge severity="unknown_severity" />);
    expect(container.firstElementChild?.className).toContain("gray");
  });

  it("appends the custom className prop", () => {
    const { container } = render(
      <SeverityBadge severity="low" className="ml-2" />
    );
    expect(container.firstElementChild?.className).toContain("ml-2");
  });
});
