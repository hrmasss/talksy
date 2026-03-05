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
import {
  RiUser3Line,
  RiBookLine,
  RiQuestionLine,
  RiTimeLine,
} from "@remixicon/react";

const stats = [
  { label: "Total Users", value: "0", icon: RiUser3Line, change: "+0%" },
  { label: "Active Exams", value: "0", icon: RiBookLine, change: "+0%" },
  { label: "Questions", value: "0", icon: RiQuestionLine, change: "+0%" },
  { label: "Sessions Today", value: "0", icon: RiTimeLine, change: "+0%" },
];

const recentActivity = [
  { user: "System", action: "Platform initialized", time: "Just now" },
];

export default function AdminDashboard() {
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
        {stats.map((stat) => (
          <Card key={stat.label} className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
                <p className="text-xl font-semibold">{stat.value}</p>
              </div>
              <stat.icon className="h-5 w-5 text-muted-foreground/50" />
            </div>
          </Card>
        ))}
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-3 pt-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="h-8 text-xs">User</TableHead>
                <TableHead className="h-8 text-xs">Action</TableHead>
                <TableHead className="h-8 text-xs text-right">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentActivity.map((activity, i) => (
                <TableRow key={i}>
                  <TableCell className="py-2 text-sm">{activity.user}</TableCell>
                  <TableCell className="py-2 text-sm">{activity.action}</TableCell>
                  <TableCell className="py-2 text-right">
                    <Badge variant="secondary" className="text-xs font-normal">
                      {activity.time}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Quick Actions - Compact */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="cursor-pointer transition-colors hover:bg-accent/50">
          <CardContent className="flex items-center gap-3 p-3">
            <RiUser3Line className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-medium">Add User</span>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-colors hover:bg-accent/50">
          <CardContent className="flex items-center gap-3 p-3">
            <RiBookLine className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-medium">Create Exam</span>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-colors hover:bg-accent/50">
          <CardContent className="flex items-center gap-3 p-3">
            <RiQuestionLine className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-medium">Add Question</span>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
