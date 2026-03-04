import React, { useEffect } from "react";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/authStore";
import { AppLayout } from "@/components/Layout/AppLayout";
import { ProtectedRoute } from "@/components/Auth/ProtectedRoute";
import { LoginPage } from "@/pages/LoginPage";
import { OAuthCallback } from "@/pages/OAuthCallback";
import { SurveyListPage } from "@/pages/SurveyListPage";
import { SurveyDetailPage } from "@/pages/SurveyDetailPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/auth/callback",
    element: <OAuthCallback />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: "/surveys",
            element: <SurveyListPage />,
          },
          {
            path: "/surveys/:surveyId",
            element: <SurveyDetailPage />,
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/surveys" replace />,
  },
]);

function AppInitializer({ children }: { children: React.ReactNode }) {
  const { initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInitializer>
        <RouterProvider router={router} />
      </AppInitializer>
    </QueryClientProvider>
  );
}
