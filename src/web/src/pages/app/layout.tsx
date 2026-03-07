import { useState } from "react";
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
  RiMicLine,
  RiBookLine,
  RiHistoryLine,
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
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

const navItems = [
  { path: "/app/dashboard", icon: RiDashboardLine, label: "Dashboard" },
  { path: "/app", icon: RiMicLine, label: "Practice", exact: true },
  { path: "/app/mock-test", icon: RiFlashlightLine, label: "Mock Test" },
  { path: "/app/daily-study", icon: RiCalendarCheckLine, label: "Study" },
  { path: "/app/progress", icon: RiBarChartLine, label: "Progress" },
];

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, setUser } = useAuth();

  const [onboardingDismissed, setOnboardingDismissed] = useState(false);

  const showOnboardingModal =
    !!user && !user.onboarding_completed && !onboardingDismissed;

  const handleSkipOnboarding = () => {
    setOnboardingDismissed(true);
  };

  const handleStartOnboarding = () => {
    setOnboardingDismissed(true);
    navigate("/app/onboarding");
  };

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <div className="flex items-center gap-8">
            <Link to="/app" className="text-lg font-semibold tracking-tight">
              Talksy
            </Link>
            <nav className="hidden items-center gap-1 md:flex">
              {navItems.map((item) => {
                const isActive = item.exact
                  ? location.pathname === item.path
                  : location.pathname.startsWith(item.path);
                return (
                  <Link key={item.path} to={item.path}>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={cn(
                        "gap-2 text-muted-foreground",
                        isActive && "bg-accent text-foreground"
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </Button>
                  </Link>
                );
              })}
            </nav>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary/10 text-primary text-sm">
                    {initials}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
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
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Mobile Navigation */}
      <nav className="sticky bottom-0 border-t border-border/50 bg-background md:hidden">
        <div className="flex items-center justify-around py-2">
          {navItems.map((item) => {
            const isActive = item.exact
              ? location.pathname === item.path
              : location.pathname.startsWith(item.path);
            return (
              <Link key={item.path} to={item.path}>
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "flex-col gap-1 h-auto py-2 text-muted-foreground",
                    isActive && "text-primary"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  <span className="text-xs">{item.label}</span>
                </Button>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Onboarding Modal */}
      <Dialog open={showOnboardingModal} onOpenChange={(open) => { if (!open) handleSkipOnboarding(); }}>
        <DialogContent showCloseButton={false} className="sm:max-w-md">
          <DialogHeader className="text-center sm:text-center">
            <div className="mx-auto mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <RiStarLine className="h-7 w-7 text-primary" />
            </div>
            <DialogTitle className="text-xl">Welcome to Talksy!</DialogTitle>
            <DialogDescription>
              Take a quick placement test to help us understand your current level
              and personalize your learning experience.
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
            <Button variant="ghost" className="w-full text-muted-foreground" onClick={handleSkipOnboarding}>
              Skip for now
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
