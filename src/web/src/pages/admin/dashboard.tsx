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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of your platform activity
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.change} from last month
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Action</TableHead>
                <TableHead className="text-right">Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentActivity.map((activity, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">{activity.user}</TableCell>
                  <TableCell>{activity.action}</TableCell>
                  <TableCell className="text-right">
                    <Badge variant="secondary" className="font-normal">
                      {activity.time}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="cursor-pointer transition-colors hover:bg-accent/50">
          <CardContent className="flex flex-col items-center justify-center py-6">
            <RiUser3Line className="h-8 w-8 text-muted-foreground mb-2" />
            <span className="text-sm font-medium">Add User</span>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-colors hover:bg-accent/50">
          <CardContent className="flex flex-col items-center justify-center py-6">
            <RiBookLine className="h-8 w-8 text-muted-foreground mb-2" />
            <span className="text-sm font-medium">Create Exam</span>
          </CardContent>
        </Card>
        <Card className="cursor-pointer transition-colors hover:bg-accent/50">
          <CardContent className="flex flex-col items-center justify-center py-6">
            <RiQuestionLine className="h-8 w-8 text-muted-foreground mb-2" />
            <span className="text-sm font-medium">Add Question</span>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
