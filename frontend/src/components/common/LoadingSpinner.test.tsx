// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LoadingSpinner from "./LoadingSpinner";

describe("LoadingSpinner", () => {
  it("renders the spinning element", () => {
    const { container } = render(<LoadingSpinner />);
    const spinner = container.querySelector(".animate-spin");
    expect(spinner).not.toBeNull();
  });

  it("renders the text when the text prop is provided", () => {
    render(<LoadingSpinner text="Loading threats..." />);
    expect(screen.getByText("Loading threats...")).toBeTruthy();
  });

  it("does not render a paragraph element when text is omitted", () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector("p")).toBeNull();
  });

  it("applies the sm size class when size is sm", () => {
    const { container } = render(<LoadingSpinner size="sm" />);
    const spinner = container.querySelector(".animate-spin");
    expect(spinner?.className).toContain("h-4");
  });

  it("applies the lg size class when size is lg", () => {
    const { container } = render(<LoadingSpinner size="lg" />);
    const spinner = container.querySelector(".animate-spin");
    expect(spinner?.className).toContain("h-12");
  });
});
