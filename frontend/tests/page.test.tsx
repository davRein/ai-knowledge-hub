import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import Home from "../app/page";

vi.mock("../components/api-status", () => ({
  ApiStatus: () => <p>API status</p>,
}));

it("clearly labels the local shell and prevents unimplemented uploads", () => {
  render(<Home />);
  expect(screen.getByText(/not production-secure/)).toBeVisible();
  expect(
    screen.getByRole("button", { name: "PDF upload coming in M2" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("link", { name: /Explore API docs/ }),
  ).toHaveAttribute("href", "http://127.0.0.1:8000/docs");
});
