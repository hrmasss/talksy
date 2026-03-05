import { Routes, Route } from "react-router-dom";
import { Suspense, lazy } from "react";

// Lazy load pages for code splitting
const MarketingPage = lazy(() => import("@/pages/marketing"));
const AppLayout = lazy(() => import("@/pages/app/layout"));
const AppHome = lazy(() => import("@/pages/app/home"));
const AdminLayout = lazy(() => import("@/pages/admin/layout"));
const AdminDashboard = lazy(() => import("@/pages/admin/dashboard"));

function LoadingSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        {/* Marketing / Landing Page */}
        <Route path="/" element={<MarketingPage />} />

        {/* User App Routes */}
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<AppHome />} />
        </Route>

        {/* Admin Routes */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
