import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";

beforeEach(() => {
  // Mock fetch: tidak ada server API di test — refresh gagal → user null
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

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

test("halaman login punya form email & password", async () => {
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <App />
    </MemoryRouter>
  );
  expect(await screen.findByLabelText("Email")).toBeInTheDocument();
  expect(screen.getByLabelText("Password")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Masuk" })).toBeInTheDocument();
});

test("halaman /app melindungi user yang belum masuk", async () => {
  render(
    <MemoryRouter initialEntries={["/app"]}>
      <App />
    </MemoryRouter>
  );
  // belum login → dialihkan ke /login
  expect(await screen.findByLabelText("Email")).toBeInTheDocument();
});
