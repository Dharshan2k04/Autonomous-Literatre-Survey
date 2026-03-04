import { Link, useNavigate } from "react-router-dom";
import {
  BookOpen,
  LogOut,
  User,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";
import { useAuthStore } from "@/store/authStore";

export function Navbar() {
  const { user, logout, isAuthenticated } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="bg-dark-900 border-b border-dark-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <BookOpen className="h-7 w-7 text-primary-500 group-hover:text-primary-400 transition-colors" />
            <span className="text-lg font-semibold text-dark-100 hidden sm:block">
              Literature Survey
            </span>
          </Link>

          {/* Desktop Nav */}
          {isAuthenticated && (
            <div className="hidden md:flex items-center gap-4">
              <Link
                to="/surveys"
                className="text-dark-300 hover:text-dark-100 text-sm font-medium transition-colors"
              >
                My Surveys
              </Link>
              <div className="flex items-center gap-3 pl-4 border-l border-dark-700">
                {user?.avatar_url ? (
                  <img
                    src={user.avatar_url}
                    alt={user.full_name}
                    className="h-8 w-8 rounded-full"
                  />
                ) : (
                  <div className="h-8 w-8 bg-primary-600 rounded-full flex items-center justify-center">
                    <User className="h-4 w-4 text-white" />
                  </div>
                )}
                <span className="text-sm text-dark-200">{user?.full_name}</span>
                <button
                  onClick={handleLogout}
                  className="text-dark-400 hover:text-red-400 transition-colors"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* Mobile menu button */}
          <button
            className="md:hidden text-dark-300"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && isAuthenticated && (
        <div className="md:hidden border-t border-dark-700 bg-dark-900 p-4 space-y-3">
          <Link
            to="/surveys"
            className="block text-dark-300 hover:text-dark-100 text-sm"
            onClick={() => setMobileOpen(false)}
          >
            My Surveys
          </Link>
          <button
            onClick={handleLogout}
            className="block text-red-400 text-sm"
          >
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
