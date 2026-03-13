import { Outlet, Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/lib/auth";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  RiDashboardLine,
  RiUser3Line,
  RiBookLine,
  RiQuestionLine,
  RiLineChartLine,
  RiFileUploadLine,
  RiSettingsLine,
  RiLogoutBoxLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";

const navItems = [
  { path: "/admin", icon: RiDashboardLine, label: "Dashboard" },
  { path: "/admin/users", icon: RiUser3Line, label: "Users" },
  { path: "/admin/exams", icon: RiBookLine, label: "Exams" },
  { path: "/admin/questions", icon: RiQuestionLine, label: "Questions" },
  { path: "/admin/analytics", icon: RiLineChartLine, label: "Analytics" },
  { path: "/admin/documents", icon: RiFileUploadLine, label: "Documents" },
];

export default function AdminLayout() {
  const location = useLocation();
  const { logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-muted/30">
      {/* Sidebar - Fixed */}
      <aside className="hidden w-52 shrink-0 lg:block">
        <div className="fixed top-0 left-0 flex h-screen w-52 flex-col border-r border-border/50 bg-background">
          <div className="flex h-12 items-center border-b border-border/50 px-4">
            <Link to="/admin" className="text-base font-semibold tracking-tight">
              Talksy Admin
            </Link>
          </div>
          <nav className="flex-1 space-y-0.5 p-2">
            {navItems.map((item) => (
              <Link key={item.path} to={item.path}>
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "w-full justify-start gap-2 text-muted-foreground h-8",
                    location.pathname === item.path &&
                      "bg-accent text-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            ))}
          </nav>
          <div className="border-t border-border/50 p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2 text-muted-foreground h-8"
              onClick={() => logout()}
            >
              <RiLogoutBoxLine className="h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="sticky top-0 z-40 flex h-12 items-center justify-between border-b border-border/50 bg-background/95 px-4 backdrop-blur supports-backdrop-filter:bg-background/60">
          <div className="flex items-center gap-4 lg:hidden">
            <Link to="/admin" className="text-base font-semibold tracking-tight">
              Talksy Admin
            </Link>
          </div>
          <div className="flex-1" />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full h-8 w-8">
                <Avatar className="h-7 w-7">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs">
                    A
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem className="gap-2 text-sm">
                <RiSettingsLine className="h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="gap-2 text-sm text-destructive focus:text-destructive"
                onClick={() => logout()}
              >
                <RiLogoutBoxLine className="h-4 w-4" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4">
          <Outlet />
        </main>
      </div>

      {/* Mobile Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 border-t border-border/50 bg-background lg:hidden">
        <div className="flex items-center justify-around py-2">
          {navItems.slice(0, 5).map((item) => (
            <Link key={item.path} to={item.path}>
              <Button
                variant="ghost"
                size="sm"
                className={cn(
                  "flex-col gap-1 h-auto py-2 text-muted-foreground",
                  location.pathname === item.path && "text-primary"
                )}
              >
                <item.icon className="h-5 w-5" />
                <span className="text-xs">{item.label}</span>
              </Button>
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
