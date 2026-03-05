import { Outlet, Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
];

export default function AdminLayout() {
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-muted/30">
      {/* Sidebar */}
      <aside className="hidden w-56 flex-col border-r border-border/50 bg-background lg:flex">
        <div className="flex h-14 items-center border-b border-border/50 px-6">
          <Link to="/admin" className="text-lg font-semibold tracking-tight">
            Talksy Admin
          </Link>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          {navItems.map((item) => (
            <Link key={item.path} to={item.path}>
              <Button
                variant="ghost"
                className={cn(
                  "w-full justify-start gap-3 text-muted-foreground",
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
        <div className="border-t border-border/50 p-4">
          <Link to="/">
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-muted-foreground"
            >
              <RiLogoutBoxLine className="h-4 w-4" />
              Back to Site
            </Button>
          </Link>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border/50 bg-background/95 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-center gap-4 lg:hidden">
            <Link to="/admin" className="text-lg font-semibold tracking-tight">
              Talksy Admin
            </Link>
          </div>
          <div className="flex-1" />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary/10 text-primary text-sm">
                    A
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem className="gap-2">
                <RiSettingsLine className="h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <Link to="/">
                <DropdownMenuItem className="gap-2">
                  <RiLogoutBoxLine className="h-4 w-4" />
                  Sign Out
                </DropdownMenuItem>
              </Link>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>

      {/* Mobile Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 border-t border-border/50 bg-background lg:hidden">
        <div className="flex items-center justify-around py-2">
          {navItems.slice(0, 4).map((item) => (
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
