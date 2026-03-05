import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  RiLineChartLine,
  RiUser3Line,
  RiBookLine,
  RiTimeLine,
} from "@remixicon/react";

const metrics = [
  { label: "Total Sessions", value: "0", icon: RiTimeLine },
  { label: "Active Users", value: "0", icon: RiUser3Line },
  { label: "Exams Completed", value: "0", icon: RiBookLine },
  { label: "Avg. Score", value: "N/A", icon: RiLineChartLine },
];

export default function AdminAnalyticsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Platform usage and performance metrics
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label} className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">{metric.label}</p>
                <p className="text-xl font-semibold">{metric.value}</p>
              </div>
              <metric.icon className="h-5 w-5 text-muted-foreground/50" />
            </div>
          </Card>
        ))}
      </div>

      {/* Charts placeholder */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium">
              Sessions Over Time
            </CardTitle>
          </CardHeader>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="text-center text-muted-foreground">
              <RiLineChartLine className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No data yet</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm font-medium">
              Score Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="text-center text-muted-foreground">
              <RiLineChartLine className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No data yet</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
