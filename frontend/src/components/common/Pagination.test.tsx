// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Pagination from "./Pagination";

describe("Pagination", () => {
  it("renders nothing when pages is 1", () => {
    const { container } = render(
      <Pagination page={1} pages={1} total={10} onPageChange={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when pages is 0", () => {
    const { container } = render(
      <Pagination page={1} pages={0} total={0} onPageChange={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows the total item count", () => {
    render(
      <Pagination page={1} pages={3} total={57} onPageChange={vi.fn()} />
    );
    expect(screen.getByText(/57 total/)).toBeTruthy();
  });

  it("shows the current page and total pages", () => {
    render(
      <Pagination page={2} pages={5} total={100} onPageChange={vi.fn()} />
    );
    expect(screen.getByText("2 / 5")).toBeTruthy();
  });

  it("disables the Previous button on the first page", () => {
    render(
      <Pagination page={1} pages={3} total={30} onPageChange={vi.fn()} />
    );
    const buttons = screen.getAllByRole("button");
    const prevButton = buttons[0];
    expect(prevButton).toHaveProperty("disabled", true);
  });

  it("disables the Next button on the last page", () => {
    render(
      <Pagination page={3} pages={3} total={30} onPageChange={vi.fn()} />
    );
    const buttons = screen.getAllByRole("button");
    const nextButton = buttons[1];
    expect(nextButton).toHaveProperty("disabled", true);
  });

  it("calls onPageChange with page - 1 when Previous is clicked", () => {
    const onPageChange = vi.fn();
    render(
      <Pagination page={3} pages={5} total={50} onPageChange={onPageChange} />
    );
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[0]);
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange with page + 1 when Next is clicked", () => {
    const onPageChange = vi.fn();
    render(
      <Pagination page={2} pages={5} total={50} onPageChange={onPageChange} />
    );
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[1]);
    expect(onPageChange).toHaveBeenCalledWith(3);
  });
});
