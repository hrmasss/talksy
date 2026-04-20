import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  RiArrowLeftLine,
  RiArrowRightLine,
  RiBookOpenLine,
  RiCheckLine,
  RiEdit2Line,
  RiFlashlightLine,
  RiHeadphoneLine,
  RiMicLine,
} from "@remixicon/react";
import { useAuth } from "@/lib/auth";
import {
  RoadmapPhaseContent,
  getPhaseCompletedCount,
  getPhaseEvaluationState,
  getPhaseTopicEntries,
  getRoadmapStorageKey,
  isPhaseEvaluationComplete,
  isPhasePracticeComplete,
  loadRoadmapPhases,
  saveRoadmapPhases,
  sectionMeta,
  togglePhaseTopicCompletion,
  type Phase,
} from "./roadmap-shared";

export default function RoadmapDetailPage() {
  const { user } = useAuth();
  const { phaseId } = useParams();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const storageKey = getRoadmapStorageKey(user.id);
  const [phases, setPhases] = useState<Phase[]>(() => loadRoadmapPhases(storageKey));

  useEffect(() => {
    setPhases(loadRoadmapPhases(storageKey));
  }, [storageKey]);

  useEffect(() => {
    saveRoadmapPhases(storageKey, phases);
  }, [phases, storageKey]);

  const phase = useMemo(
    () => phases.find((item) => item.id === Number(phaseId)),
    [phases, phaseId]
  );

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

  const topicEntries = getPhaseTopicEntries(phase);
  const phaseIdNumber = phase.id;
  const completedCount = getPhaseCompletedCount(phase);
  const totalCount = topicEntries.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const practiceComplete = isPhasePracticeComplete(phase);
  const evaluationComplete = isPhaseEvaluationComplete(phase);
  const evaluationState = getPhaseEvaluationState(phase);
  const evaluationLink = `/app/mock-test?section=full&roadmapEvaluation=1&roadmapPhaseId=${phaseIdNumber}`;

  function handleToggleTopic(topicId: string) {
    setPhases((current) => togglePhaseTopicCompletion(current, phaseIdNumber, topicId));
  }

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
          <Badge
            variant={evaluationComplete ? "default" : "secondary"}
            className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]"
          >
            {evaluationState === "completed"
              ? "Evaluation Completed"
              : evaluationState === "ready"
                ? "Ready For Exam"
                : "Practice In Progress"}
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

      <div className="mb-8 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <Card className="border border-border shadow-none">
          <CardHeader>
            <CardTitle className="text-xl">Phase Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="text-3xl font-semibold">{progressPercent}%</p>
                <p className="text-sm text-muted-foreground">
                  {completedCount}/{totalCount} roadmap items completed
                </p>
              </div>
              <Badge variant="outline" className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em]">
                {practiceComplete ? "Practice Done" : "Keep Going"}
              </Badge>
            </div>
            <div className="h-3 overflow-hidden border border-border bg-background">
              <div className="h-full bg-primary transition-all" style={{ width: `${progressPercent}%` }} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {topicEntries.map((topic) => {
                const meta = sectionMeta[topic.section];
                const isDone = phase.completed_topic_ids.includes(topic.id);
                return (
                  <button
                    key={topic.id}
                    onClick={() => handleToggleTopic(topic.id)}
                    className="flex items-center gap-3 border border-border bg-background px-4 py-4 text-left transition-colors hover:border-primary/30 hover:bg-accent/10"
                  >
                    <div className={`flex h-10 w-10 items-center justify-center border ${meta.bg} ${meta.border}`}>
                      {isDone ? (
                        <RiCheckLine className="h-5 w-5 text-emerald-600" />
                      ) : (
                        <meta.icon className={`h-5 w-5 ${meta.color}`} />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{topic.title}</p>
                      <p className="text-xs text-muted-foreground">{topic.detail}</p>
                    </div>
                    <Badge variant={isDone ? "default" : "secondary"} className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]">
                      {isDone ? "Done" : "Open"}
                    </Badge>
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border shadow-none">
          <CardHeader>
            <CardTitle className="text-xl">Evaluation Gate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {!practiceComplete ? (
              <div className="space-y-3">
                <p className="text-[15px] leading-7 text-foreground/90">
                  Finish all roadmap items first. Once every topic is completed, the evaluation exam unlocks and becomes the requirement for moving to the next phase.
                </p>
                <div className="border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Next phase is locked until this phase is practiced and evaluated.
                </div>
              </div>
            ) : evaluationComplete && phase.evaluation_report ? (
              <div className="space-y-4">
                <div className="border border-emerald-200 bg-emerald-50 p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                        Evaluation Result
                      </p>
                      <p className="mt-1 text-lg font-semibold text-emerald-900">
                        Full Test Evaluation Saved
                      </p>
                    </div>
                    {phase.evaluation_report.overall_band != null && (
                      <div className="text-right">
                        <p className="text-3xl font-semibold text-emerald-900">
                          {phase.evaluation_report.overall_band}
                        </p>
                        <p className="text-xs uppercase tracking-[0.12em] text-emerald-700">
                          Overall Band
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {phase.evaluation_report.section_scores.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      Section Scores
                    </p>
                    <div className="space-y-2">
                      {phase.evaluation_report.section_scores.map((score, index) => (
                        <div key={`${score.section}-${index}`} className="flex items-center justify-between border border-border bg-background px-4 py-3 text-sm">
                          <span className="capitalize">{score.section}</span>
                          <span className="font-semibold">{score.band_score ?? "N/A"}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button asChild className="h-11 px-5 text-base">
                    <Link to="/app/roadmap">
                      Back to Roadmap Library
                      <RiArrowRightLine className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                  <Button asChild variant="outline" className="h-11 px-5 text-base">
                    <Link to={evaluationLink}>Retake Evaluation</Link>
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-[15px] leading-7 text-foreground/90">
                  Practice is complete. Start a full mock test now to evaluate this phase before generating the next one.
                </p>
                <div className="border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                  This evaluation uses the full mock test flow and saves the report back into this roadmap phase.
                </div>
                <Button asChild size="lg" className="h-12 px-6 text-base">
                  <Link to={evaluationLink}>
                    <RiFlashlightLine className="mr-2 h-4 w-4" />
                    Start Phase Evaluation
                  </Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mb-8 border border-violet-200 bg-violet-50/70 p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center border border-violet-200 bg-white">
            <RiMicLine className="h-5 w-5 text-violet-700" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-violet-900">Speaking Time Rule</p>
            <p className="text-sm leading-6 text-violet-900/90">
              Keep each speaking answer practical and concise. One answer should never aim for more than 5 minutes, and most roadmap speaking responses should stay well below that.
            </p>
          </div>
        </div>
      </div>

      <RoadmapPhaseContent phase={phase} />
    </div>
  );
}
