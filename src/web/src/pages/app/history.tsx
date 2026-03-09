import { Card, CardContent } from "@/components/ui/card";
import { RiHistoryLine } from "@remixicon/react";

export default function HistoryPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">History</h1>
        <p className="text-muted-foreground">
          View your past practice sessions and exam attempts
        </p>
      </div>

      {/* Empty State */}
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <RiHistoryLine className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="font-medium">No history yet</h3>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Start practicing to see your session history and track your progress
            over time.
          </p>
        </CardContent>
      </Card>

      {/* This would show when there's history:
      <div className="space-y-3">
        {sessions.map((session) => (
          <Card key={session.id}>
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                {session.type === "speaking" ? (
                  <RiMicLine className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <RiBookLine className="h-5 w-5 text-muted-foreground" />
                )}
                <div>
                  <p className="font-medium">{session.title}</p>
                  <p className="text-sm text-muted-foreground">{session.date}</p>
                </div>
              </div>
              <Badge variant="secondary">{session.score}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
      */}
    </div>
  );
}
