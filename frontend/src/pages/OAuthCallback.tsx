import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/services/endpoints";

export function OAuthCallback() {
  const [params] = useSearchParams();
  const { setUser } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");

    if (accessToken && refreshToken) {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);

      authApi.getMe().then((res) => {
        setUser(res.data, accessToken, refreshToken);
        navigate("/surveys");
      }).catch(() => {
        navigate("/login");
      });
    } else {
      navigate("/login");
    }
  }, [params, setUser, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500" />
    </div>
  );
}
