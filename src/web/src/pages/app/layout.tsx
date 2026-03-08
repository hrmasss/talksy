import { createContext, useCallback, useContext, useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  RiMicLine,
  RiLogoutBoxLine,
  RiSettingsLine,
  RiUser3Line,
  RiDashboardLine,
  RiFlashlightLine,
  RiBarChartLine,
  RiCalendarCheckLine,
  RiStarLine,
  RiHeadphoneLine,
  RiBookOpenLine,
  RiEdit2Line,
  RiVoiceprintLine,
  RiRoadMapLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

// ── Onboarding Gate Context ──────────────────────────────────
interface OnboardingGateContextValue {
  requireOnboarding: () => boolean;
}

const OnboardingGateContext = createContext<OnboardingGateContextValue | null>(null);

/**
 * Hook for child pages to gate features behind onboarding.
 * Call `requireOnboarding()` before starting any exam/feature.
 * Returns `true` if the user still needs onboarding (modal was shown),
 * `false` if they can proceed.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useOnboardingGate() {
  const ctx = useContext(OnboardingGateContext);
  if (!ctx) throw new Error("useOnboardingGate must be used within AppLayout");
  return ctx;
}

// ── Nav items ────────────────────────────────────────────────
const mainNavItems = [
  { path: "/app/dashboard", icon: RiDashboardLine, label: "Dashboard" },
  { path: "/app", icon: RiMicLine, label: "Practice", exact: true },
  { path: "/app/mock-test", icon: RiFlashlightLine, label: "Mock Test", gated: true },
  { path: "/app/daily-study", icon: RiCalendarCheckLine, label: "Study", gated: true },
  { path: "/app/roadmap", icon: RiRoadMapLine, label: "Roadmap", gated: true },
  { path: "/app/progress", icon: RiBarChartLine, label: "Progress", gated: true },
];

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [showOnboardingModal, setShowOnboardingModal] = useState(false);

  // Show the welcome modal on first load if not onboarded
  const [welcomeShown, setWelcomeShown] = useState(() => {
    return !!user && !user.onboarding_completed;
  });

  const handleDismissWelcome = () => setWelcomeShown(false);
  const handleDismissGate = () => setShowOnboardingModal(false);

  const handleStartOnboarding = () => {
    setWelcomeShown(false);
    setShowOnboardingModal(false);
    navigate("/app/onboarding");
  };

  // Gate function: returns true if blocked (modal shown), false if OK to proceed
  const requireOnboarding = useCallback(() => {
    if (!user || user.onboarding_completed) return false;
    setShowOnboardingModal(true);
    return true;
  }, [user]);

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  const isModalOpen = welcomeShown || showOnboardingModal;
  const dismissModal = welcomeShown ? handleDismissWelcome : handleDismissGate;

  return (
    <OnboardingGateContext.Provider value={{ requireOnboarding }}>
      <SidebarProvider>
        {/* ── Sidebar ──────────────────────────────────── */}
        <Sidebar variant="sidebar" collapsible="icon">
          <SidebarHeader>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton size="lg" asChild>
                  <Link to="/app">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                      <RiMicLine className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col gap-0.5 leading-none">
                      <span className="font-semibold">Talksy</span>
                      <span className="text-xs text-muted-foreground">IELTS Prep</span>
                    </div>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarHeader>

          <SidebarSeparator />

          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Navigation</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {mainNavItems.map((item) => {
                    const isActive = item.exact
                      ? location.pathname === item.path
                      : location.pathname.startsWith(item.path);

                    return (
                      <SidebarMenuItem key={item.path}>
                        <SidebarMenuButton
                          isActive={isActive}
                          tooltip={item.label}
                          asChild={!item.gated || !user || user.onboarding_completed}
                          onClick={
                            item.gated && user && !user.onboarding_completed
                              ? (e: React.MouseEvent) => {
                                  e.preventDefault();
                                  setShowOnboardingModal(true);
                                }
                              : undefined
                          }
                        >
                          {item.gated && user && !user.onboarding_completed ? (
                            <span className="flex items-center gap-2 opacity-60">
                              <item.icon className="h-4 w-4" />
                              <span>{item.label}</span>
                            </span>
                          ) : (
                            <Link to={item.path}>
                              <item.icon className="h-4 w-4" />
                              <span>{item.label}</span>
                            </Link>
                          )}
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          <SidebarFooter>
            <SidebarMenu>
              <SidebarMenuItem>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <SidebarMenuButton size="lg">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary/10 text-primary text-xs">
                          {initials}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex flex-col gap-0.5 leading-none">
                        <span className="text-sm font-medium truncate">
                          {user?.full_name || "User"}
                        </span>
                        <span className="text-xs text-muted-foreground truncate">
                          {user?.email || ""}
                        </span>
                      </div>
                    </SidebarMenuButton>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    side="top"
                    align="start"
                    className="w-[--radix-dropdown-menu-trigger-width]"
                  >
                    <DropdownMenuItem className="gap-2">
                      <RiUser3Line className="h-4 w-4" />
                      Profile
                    </DropdownMenuItem>
                    <DropdownMenuItem className="gap-2">
                      <RiSettingsLine className="h-4 w-4" />
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="gap-2 text-destructive"
                      onClick={() => {
                        logout();
                        navigate("/login");
                      }}
                    >
                      <RiLogoutBoxLine className="h-4 w-4" />
                      Sign Out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        </Sidebar>

        {/* ── Main Area ────────────────────────────────── */}
        <SidebarInset>
          <header className="sticky top-0 z-40 flex h-12 items-center gap-2 border-b border-border/50 bg-background/95 px-4 backdrop-blur supports-backdrop-filter:bg-background/60">
            <SidebarTrigger />
            <span className="text-sm font-medium text-muted-foreground">
              {mainNavItems.find((i) =>
                i.exact
                  ? location.pathname === i.path
                  : location.pathname.startsWith(i.path)
              )?.label || "Talksy"}
            </span>
          </header>

          <main className="flex-1">
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>

      {/* ── Onboarding Modal (welcome + gate) ────────── */}
      <Dialog open={isModalOpen} onOpenChange={(open) => { if (!open) dismissModal(); }}>
        <DialogContent showCloseButton={false} className="sm:max-w-md">
          <DialogHeader className="text-center sm:text-center">
            <div className="mx-auto mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <RiStarLine className="h-7 w-7 text-primary" />
            </div>
            <DialogTitle className="text-xl">
              {welcomeShown ? "Welcome to Talksy!" : "Complete Onboarding First"}
            </DialogTitle>
            <DialogDescription>
              {welcomeShown
                ? "Take a quick placement test to help us understand your current level and personalize your learning experience."
                : "You need to complete the placement test before accessing this feature. It helps us personalize your learning path."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-2 py-2">
            {[
              { icon: RiHeadphoneLine, label: "Listening", color: "text-blue-600 bg-blue-500/10" },
              { icon: RiBookOpenLine, label: "Reading", color: "text-emerald-600 bg-emerald-500/10" },
              { icon: RiEdit2Line, label: "Writing", color: "text-amber-600 bg-amber-500/10" },
              { icon: RiVoiceprintLine, label: "Speaking", color: "text-purple-600 bg-purple-500/10" },
            ].map((s) => (
              <div key={s.label} className="flex items-center gap-2 rounded-lg border border-border/50 p-2.5 text-sm">
                <div className={cn("flex h-7 w-7 items-center justify-center rounded-md", s.color)}>
                  <s.icon className="h-3.5 w-3.5" />
                </div>
                {s.label}
              </div>
            ))}
          </div>

          <p className="text-center text-xs text-muted-foreground">
            Takes about 15 minutes — 2-3 questions per section
          </p>

          <DialogFooter className="flex-col gap-2 sm:flex-col">
            <Button className="w-full" size="lg" onClick={handleStartOnboarding}>
              Start Placement Test
            </Button>
            <Button variant="ghost" className="w-full text-muted-foreground" onClick={dismissModal}>
              {welcomeShown ? "Skip for now" : "Go back"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </OnboardingGateContext.Provider>
  );
}
