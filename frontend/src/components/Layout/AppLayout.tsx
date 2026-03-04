import { Outlet } from "react-router-dom";
import { Navbar } from "./Navbar";
import { Toaster } from "sonner";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-dark-950">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      <Toaster
        position="top-right"
        theme="dark"
        toastOptions={{
          style: {
            background: "#1e293b",
            border: "1px solid #334155",
            color: "#e2e8f0",
          },
        }}
      />
    </div>
  );
}
