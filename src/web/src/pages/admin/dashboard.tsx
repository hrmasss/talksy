import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  RiUser3Line,
  RiBookLine,
  RiQuestionLine,
  RiTimeLine,
  RiDatabase2Line,
} from "@remixicon/react";
import { getAdminStats, listModels, type AdminStats, type ModelInfo } from "@/lib/admin-api";

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, modelsData] = await Promise.all([
          getAdminStats(),
          listModels(),
        ]);
        setStats(statsData);
        setModels(modelsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-destructive">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 text-sm text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  const statCards = [
    { label: "Total Users", value: stats?.total_users ?? 0, icon: RiUser3Line },
    { label: "Active Exams", value: stats?.total_exams ?? 0, icon: RiBookLine },
    { label: "Questions", value: stats?.total_questions ?? 0, icon: RiQuestionLine },
    { label: "Conversations", value: stats?.total_conversations ?? 0, icon: RiTimeLine },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of your platform activity
        </p>
      </div>

      {/* Stats Grid - Compact */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.label} className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
                {loading ? (
                  <Skeleton className="h-7 w-16 mt-1" />
                ) : (
                  <p className="text-xl font-semibold">{stat.value}</p>
                )}
              </div>
              <stat.icon className="h-5 w-5 text-muted-foreground/50" />
            </div>
          </Card>
        ))}
      </div>

      {/* Models Overview */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <RiDatabase2Line className="h-4 w-4" />
            Database Models
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-3 pt-0">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="h-8 text-xs">Model</TableHead>
                  <TableHead className="h-8 text-xs">Description</TableHead>
                  <TableHead className="h-8 text-xs text-right">Records</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {models.map((model) => (
                  <TableRow key={model.name}>
                    <TableCell className="py-2">
                      <Link
                        to={`/admin/models/${model.name}`}
                        className="text-sm font-medium text-primary hover:underline"
                      >
                        {model.display_name}
                      </Link>
                    </TableCell>
                    <TableCell className="py-2 text-sm text-muted-foreground">
                      {model.description}
                    </TableCell>
                    <TableCell className="py-2 text-right">
                      <Badge variant="secondary" className="text-xs font-normal">
                        {model.count}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions - Compact */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Link to="/admin/users">
          <Card className="cursor-pointer transition-colors hover:bg-accent/50">
            <CardContent className="flex items-center gap-3 p-3">
              <RiUser3Line className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium">Manage Users</span>
            </CardContent>
          </Card>
        </Link>
        <Link to="/admin/models/exams">
          <Card className="cursor-pointer transition-colors hover:bg-accent/50">
            <CardContent className="flex items-center gap-3 p-3">
              <RiBookLine className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium">Manage Exams</span>
            </CardContent>
          </Card>
        </Link>
        <Link to="/admin/models/questions">
          <Card className="cursor-pointer transition-colors hover:bg-accent/50">
            <CardContent className="flex items-center gap-3 p-3">
              <RiQuestionLine className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium">Manage Questions</span>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
