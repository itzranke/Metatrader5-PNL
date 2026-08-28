import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";

test("landing page menampilkan CTA utama", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>
  );
  expect(screen.getByRole("heading", { name: /MT5 Journal/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Daftar Gratis" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Masuk" })).toBeInTheDocument();
});
