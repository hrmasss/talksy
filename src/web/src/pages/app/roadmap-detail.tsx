import { Link, Navigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiArrowLeftLine, RiBookOpenLine, RiHeadphoneLine, RiEdit2Line, RiMicLine } from "@remixicon/react";
import { useAuth } from "@/lib/auth";
import {
  RoadmapPhaseContent,
  getRoadmapStorageKey,
  loadRoadmapPhases,
  type Phase,
} from "./roadmap-shared";

export default function RoadmapDetailPage() {
  const { user } = useAuth();
  const { phaseId } = useParams();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const phases = loadRoadmapPhases(getRoadmapStorageKey(user.id));
  const phase = phases.find((item) => item.id === Number(phaseId)) as Phase | undefined;

  if (!phase) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8">
        <Button asChild variant="ghost" size="sm" className="mb-4 gap-2">
          <Link to="/app/roadmap">
            <RiArrowLeftLine className="h-4 w-4" />
            Back to Roadmap
          </Link>
        </Button>

        <Card>
          <CardHeader>
            <CardTitle>Phase not found</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              This roadmap phase is not available in local storage anymore.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const topicCounts = [
    { label: "Speaking", count: phase.topics.speaking_topics.length, icon: RiMicLine },
    { label: "Writing", count: phase.topics.writing_topics.length, icon: RiEdit2Line },
    { label: "Reading", count: phase.topics.reading_topics.length, icon: RiBookOpenLine },
    { label: "Listening", count: phase.topics.listening_topics.length, icon: RiHeadphoneLine },
  ].filter((item) => item.count > 0);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <Button asChild variant="ghost" size="sm" className="mb-4 gap-2 text-sm">
        <Link to="/app/roadmap">
          <RiArrowLeftLine className="h-4 w-4" />
          Back to Roadmap
        </Link>
      </Button>

      <div className="mb-8 space-y-4 border-b border-border pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-4xl font-semibold tracking-tight">{phase.title}</h1>
          <Badge variant={phase.status === "active" ? "default" : "secondary"} className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
            {phase.status === "active" ? "Current Version" : "Saved Version"}
          </Badge>
        </div>
        <p className="max-w-4xl text-lg leading-8 text-muted-foreground">{phase.description}</p>
        {topicCounts.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {topicCounts.map((item) => (
              <Badge key={item.label} variant="outline" className="gap-1 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
                <item.icon className="h-3 w-3" />
                {item.count} {item.label}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <RoadmapPhaseContent phase={phase} />
    </div>
  );
}
