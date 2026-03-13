import { Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import { AuthProvider, useAuth } from "@/lib/auth";

// Lazy load pages for code splitting
const MarketingPage = lazy(() => import("@/pages/marketing"));
const LoginPage = lazy(() => import("@/pages/login"));
const SignupPage = lazy(() => import("@/pages/signup"));

// User App
const AppLayout = lazy(() => import("@/pages/app/layout"));
const AppHome = lazy(() => import("@/pages/app/home"));
const AppExams = lazy(() => import("@/pages/app/exams"));
const AppHistory = lazy(() => import("@/pages/app/history"));
const AppDashboard = lazy(() => import("@/pages/app/dashboard"));
const AppOnboarding = lazy(() => import("@/pages/app/onboarding"));
const AppMockTest = lazy(() => import("@/pages/app/mock-test"));
const AppDailyStudy = lazy(() => import("@/pages/app/daily-study"));
const AppDailyStudyDetail = lazy(() => import("@/pages/app/daily-study-detail"));
const AppProgress = lazy(() => import("@/pages/app/progress"));
const AppRoadmap = lazy(() => import("@/pages/app/roadmap"));
const AppRoadmapDetail = lazy(() => import("@/pages/app/roadmap-detail"));
const AppSettings = lazy(() => import("@/pages/app/settings"));

// Admin
const AdminLayout = lazy(() => import("@/pages/admin/layout"));
const AdminDashboard = lazy(() => import("@/pages/admin/dashboard"));
const AdminUsers = lazy(() => import("@/pages/admin/users"));
const AdminExams = lazy(() => import("@/pages/admin/exams"));
const AdminQuestions = lazy(() => import("@/pages/admin/questions"));
const AdminAnalytics = lazy(() => import("@/pages/admin/analytics"));
const AdminModelBrowser = lazy(() => import("@/pages/admin/model-browser"));
const AdminDocuments = lazy(() => import("@/pages/admin/documents"));

function LoadingSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}

/** Redirects admins to /admin, requires authentication for regular users */
function RequireUser({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  // Admins should use admin dashboard, not regular app
  if (user?.role === "admin") return <Navigate to="/admin" replace />;
  return <>{children}</>;
}

/** Redirects to /app if not admin */
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role !== "admin") return <Navigate to="/app" replace />;
  return <>{children}</>;
}

/** Redirects to /admin for admins, /app for regular users */
function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <LoadingSpinner />;
  if (isAuthenticated) {
    const redirectTo = user?.role === "admin" ? "/admin" : "/app";
    return <Navigate to={redirectTo} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          {/* Marketing / Landing Page */}
          <Route path="/" element={<MarketingPage />} />

          {/* Auth Pages — redirect to appropriate dashboard */}
          <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
          <Route path="/signup" element={<GuestOnly><SignupPage /></GuestOnly>} />

          {/* User App Routes — admins redirected to /admin */}
          <Route path="/app" element={<RequireUser><AppLayout /></RequireUser>}>
            <Route index element={<AppHome />} />
            <Route path="exams" element={<AppExams />} />
            <Route path="history" element={<AppHistory />} />
            <Route path="dashboard" element={<AppDashboard />} />
            <Route path="onboarding" element={<AppOnboarding />} />
            <Route path="mock-test" element={<AppMockTest />} />
            <Route path="daily-study" element={<AppDailyStudy />} />
            <Route path="daily-study/:planId" element={<AppDailyStudyDetail />} />
            <Route path="progress" element={<AppProgress />} />
            <Route path="roadmap" element={<AppRoadmap />} />
            <Route path="roadmap/:phaseId" element={<AppRoadmapDetail />} />
            <Route path="settings" element={<AppSettings />} />
          </Route>

          {/* Admin Routes — require admin role */}
          <Route path="/admin" element={<RequireAdmin><AdminLayout /></RequireAdmin>}>
            <Route index element={<AdminDashboard />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="exams" element={<AdminExams />} />
            <Route path="questions" element={<AdminQuestions />} />
            <Route path="analytics" element={<AdminAnalytics />} />
            <Route path="documents" element={<AdminDocuments />} />
            <Route path="models/:modelName" element={<AdminModelBrowser />} />
          </Route>
        </Routes>
      </Suspense>
    </AuthProvider>
  );
}
