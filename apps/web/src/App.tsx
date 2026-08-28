import { Route, Routes } from "react-router-dom";
import { AppShell } from "./pages/AppShell";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Login register />} />
      <Route path="/app/*" element={<AppShell />} />
    </Routes>
  );
}
