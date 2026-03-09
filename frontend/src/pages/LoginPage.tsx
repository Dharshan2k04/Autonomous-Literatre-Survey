import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { BookOpen, Github, Mail } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/services/endpoints";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

const registerSchema = loginSchema.extend({
  full_name: z.string().min(1, "Full name is required").max(255),
});

type LoginForm = z.infer<typeof loginSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

export function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuthStore();
  const navigate = useNavigate();

  const loginForm = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const registerForm = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const handleLogin = async (data: LoginForm) => {
    setLoading(true);
    try {
      const res = await authApi.login(data);
      setUser(res.data.user, res.data.tokens.access_token, res.data.tokens.refresh_token);
      toast.success("Logged in successfully");
      navigate("/surveys");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: { message?: string } } } };
      toast.error(error.response?.data?.error?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (data: RegisterForm) => {
    setLoading(true);
    try {
      const res = await authApi.register(data);
      setUser(res.data.user, res.data.tokens.access_token, res.data.tokens.refresh_token);
      toast.success("Account created successfully");
      navigate("/surveys");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { error?: { message?: string } } } };
      toast.error(error.response?.data?.error?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const API_URL = import.meta.env.VITE_API_URL || "";

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-950 px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <BookOpen className="h-12 w-12 text-primary-500" />
          </div>
          <h1 className="text-2xl font-bold text-dark-50">Autonomous Literature Survey</h1>
          <p className="text-dark-400 mt-2">AI-powered academic literature review</p>
        </div>

        <div className="card">
          {/* Tab switch */}
          <div className="flex mb-6 border-b border-dark-700">
            <button
              onClick={() => setIsRegister(false)}
              className={`flex-1 pb-3 text-sm font-medium transition-colors ${
                !isRegister
                  ? "text-primary-400 border-b-2 border-primary-400"
                  : "text-dark-400 hover:text-dark-200"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setIsRegister(true)}
              className={`flex-1 pb-3 text-sm font-medium transition-colors ${
                isRegister
                  ? "text-primary-400 border-b-2 border-primary-400"
                  : "text-dark-400 hover:text-dark-200"
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Login Form */}
          {!isRegister ? (
            <form onSubmit={loginForm.handleSubmit(handleLogin)} className="space-y-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1.5">Email</label>
                <input
                  {...loginForm.register("email")}
                  type="email"
                  className="input-field"
                  placeholder="you@example.com"
                />
                {loginForm.formState.errors.email && (
                  <p className="text-red-400 text-xs mt-1">
                    {loginForm.formState.errors.email.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1.5">Password</label>
                <input
                  {...loginForm.register("password")}
                  type="password"
                  className="input-field"
                  placeholder="••••••••"
                />
                {loginForm.formState.errors.password && (
                  <p className="text-red-400 text-xs mt-1">
                    {loginForm.formState.errors.password.message}
                  </p>
                )}
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? "Signing in..." : "Sign In"}
              </button>
            </form>
          ) : (
            /* Register Form */
            <form onSubmit={registerForm.handleSubmit(handleRegister)} className="space-y-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1.5">Full Name</label>
                <input
                  {...registerForm.register("full_name")}
                  type="text"
                  className="input-field"
                  placeholder="John Doe"
                />
                {registerForm.formState.errors.full_name && (
                  <p className="text-red-400 text-xs mt-1">
                    {registerForm.formState.errors.full_name.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1.5">Email</label>
                <input
                  {...registerForm.register("email")}
                  type="email"
                  className="input-field"
                  placeholder="you@example.com"
                />
                {registerForm.formState.errors.email && (
                  <p className="text-red-400 text-xs mt-1">
                    {registerForm.formState.errors.email.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1.5">Password</label>
                <input
                  {...registerForm.register("password")}
                  type="password"
                  className="input-field"
                  placeholder="••••••••"
                />
                {registerForm.formState.errors.password && (
                  <p className="text-red-400 text-xs mt-1">
                    {registerForm.formState.errors.password.message}
                  </p>
                )}
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? "Creating account..." : "Create Account"}
              </button>
            </form>
          )}

          {/* OAuth Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-dark-700" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-dark-900 px-2 text-dark-400">or continue with</span>
            </div>
          </div>

          {/* OAuth Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <a
              href={`${API_URL}/api/v1/auth/google/login`}
              className="btn-secondary flex items-center justify-center gap-2 text-sm"
            >
              <Mail className="h-4 w-4" />
              Google
            </a>
            <a
              href={`${API_URL}/api/v1/auth/github/login`}
              className="btn-secondary flex items-center justify-center gap-2 text-sm"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
