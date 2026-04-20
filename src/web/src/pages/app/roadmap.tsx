import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  RiArrowRightLine,
  RiBookOpenLine,
  RiEdit2Line,
  RiFlashlightLine,
  RiHeadphoneLine,
  RiLoader4Line,
  RiMicLine,
  RiRoadMapLine,
  RiStackLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { getUserFacingErrorMessage } from "@/lib/app-errors";
import { useOnboardingGate } from "./onboarding-gate";
import { generateTopics } from "@/lib/ielts-api";
import { toast } from "sonner";
import {
  getPhaseTitle,
  getRoadmapStorageKey,
  loadRoadmapPhases,
  sectionMeta,
  type Phase,
} from "./roadmap-shared";

const roadmapSections = [
  { key: "speaking", label: "Speaking", icon: RiMicLine },
  { key: "writing", label: "Writing", icon: RiEdit2Line },
  { key: "reading", label: "Reading", icon: RiBookOpenLine },
  { key: "listening", label: "Listening", icon: RiHeadphoneLine },
] as const;

export default function RoadmapPage() {
  const { user } = useAuth();
  const { requireOnboarding } = useOnboardingGate();
  const roadmapStorageKey = getRoadmapStorageKey(user?.id);

  const [phases, setPhases] = useState<Phase[]>(() => loadRoadmapPhases(roadmapStorageKey));
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!roadmapStorageKey) return;
    if (phases.length > 0) {
      localStorage.setItem(roadmapStorageKey, JSON.stringify(phases));
      return;
    }
    localStorage.removeItem(roadmapStorageKey);
  }, [phases, roadmapStorageKey]);

  useEffect(() => {
    setPhases(loadRoadmapPhases(roadmapStorageKey));
  }, [roadmapStorageKey]);

  const activePhase = useMemo(
    () => phases.find((phase) => phase.status === "active") ?? phases.at(-1) ?? null,
    [phases]
  );

  async function handleGenerate() {
    if (!user || requireOnboarding()) return;

    setGenerating(true);
    setError("");

    try {
      const result = await generateTopics(user.id, {
        target_score: user.target_band_score ?? 7.0,
        current_level_description: user.current_estimated_band
          ? `Currently at band ${user.current_estimated_band}`
          : undefined,
      });

      const nextPhaseNum = phases.length + 1;
      const newPhase: Phase = {
        id: nextPhaseNum,
        title: `${getPhaseTitle(nextPhaseNum, result)}`,
        description:
          result.assessment_summary ||
          result.study_plan_notes ||
          `Focus on: ${result.weaknesses.slice(0, 2).join(", ") || "all sections"}`,
        topics: result,
        status: "active",
      };

      setPhases((current) => [
        ...current.map((phase) => ({ ...phase, status: "saved" as const })),
        newPhase,
      ]);
      toast.success("Your roadmap is ready.");
    } catch (e) {
      const message = getUserFacingErrorMessage(
        e,
        "Couldn't generate your roadmap. Please try again."
      );
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  }

  if (phases.length === 0) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-10">
        <Card className="overflow-hidden border border-border bg-card shadow-none">
          <CardContent className="grid gap-10 p-8 lg:grid-cols-[1.1fr_0.9fr] lg:p-10">
            <div className="space-y-6">
              <div className="flex h-16 w-16 items-center justify-center border border-primary/20 bg-primary/10">
                <RiRoadMapLine className="h-9 w-9 text-primary" />
              </div>
              <div className="space-y-4">
                <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-balance">
                  Build a study roadmap with detailed practice for all four IELTS skills.
                </h1>
                <p className="max-w-2xl text-lg leading-8 text-muted-foreground">
                  This roadmap gives the student 4 Speaking, 4 Writing, 4 Reading, and
                  4 Listening practice items in one place. It is for guided practice only,
                  so there is no evaluation gate in this phase.
                </p>
              </div>

              {error && (
                <div className="max-w-2xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="grid gap-3 sm:grid-cols-2">
                {roadmapSections.map((section) => {
                  const meta = sectionMeta[section.key];
                  return (
                    <div
                      key={section.key}
                      className="flex items-center gap-4 border border-border bg-background px-4 py-4"
                    >
                      <div
                        className={cn(
                          "flex h-11 w-11 items-center justify-center border",
                          meta.bg,
                          meta.border
                        )}
                      >
                        <section.icon className={cn("h-5 w-5", meta.color)} />
                      </div>
                      <div>
                        <div className="text-base font-semibold">{section.label}</div>
                        <div className="text-sm text-muted-foreground">4 detailed practice items</div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <Button size="lg" className="h-12 px-6 text-base" onClick={handleGenerate} disabled={generating}>
                {generating ? (
                  <>
                    <RiLoader4Line className="h-4 w-4 animate-spin" />
                    Building roadmap...
                  </>
                ) : (
                  <>
                    <RiFlashlightLine className="h-4 w-4" />
                    Generate Roadmap
                  </>
                )}
              </Button>
            </div>

            <div className="border border-border bg-muted/20 p-6">
              <div className="mb-5 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center border border-border bg-background">
                  <RiStackLine className="h-5 w-5 text-foreground" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">What the student gets</h2>
                  <p className="text-sm text-muted-foreground">Clear practice, not a confusing dump of prompts</p>
                </div>
              </div>
              <div className="space-y-4 text-[15px] leading-7 text-foreground/90">
                <p>Each roadmap item includes practical guidance, student-friendly language, and enough detail to start studying immediately.</p>
                <p>Speaking and writing include structure help. Reading and listening include strategy guidance instead of only topic names.</p>
                <p>The roadmap is saved locally, so you can generate a fresh version later and compare versions as the product improves.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-3">
          <Badge variant="outline" className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]">
            Roadmap Library
          </Badge>
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">Study Roadmap</h1>
            <p className="mt-2 max-w-3xl text-lg leading-8 text-muted-foreground">
              Every roadmap version includes 4 Speaking, 4 Writing, 4 Reading, and
              4 Listening items with more explanation and no quiz gate.
            </p>
          </div>
        </div>

        <Button className="h-12 px-6 text-base" onClick={handleGenerate} disabled={generating}>
          {generating ? (
            <>
              <RiLoader4Line className="h-4 w-4 animate-spin" />
              Updating roadmap...
            </>
          ) : (
            <>
              <RiFlashlightLine className="h-4 w-4" />
              Generate New Version
            </>
          )}
        </Button>
      </div>

      {error && (
        <div className="mb-6 border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {activePhase && (
        <Card className="mb-8 border border-primary/20 bg-primary/5 shadow-none">
          <CardContent className="flex flex-col gap-4 p-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
                  Current Version
                </Badge>
                <span className="text-sm text-muted-foreground">Roadmap {activePhase.id}</span>
              </div>
              <h2 className="text-2xl font-semibold">{activePhase.title}</h2>
              <p className="max-w-3xl text-[15px] leading-7 text-foreground/85">
                {activePhase.description}
              </p>
            </div>
            <Button asChild size="lg" className="h-11 px-5 text-base">
              <Link to={`/app/roadmap/${activePhase.id}`}>
                Open Current Roadmap
                <RiArrowRightLine className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {phases
          .slice()
          .reverse()
          .map((phase) => {
            const isActive = phase.status === "active";

            return (
              <Card
                key={phase.id}
                className={cn(
                  "border shadow-none transition-colors",
                  isActive ? "border-primary/30 bg-card" : "border-border bg-card/90"
                )}
              >
                <CardHeader className="space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          variant={isActive ? "default" : "secondary"}
                          className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]"
                        >
                          {isActive ? "Current" : "Saved"}
                        </Badge>
                        <span className="text-sm text-muted-foreground">Roadmap {phase.id}</span>
                      </div>
                      <CardTitle className="text-2xl font-semibold">{phase.title}</CardTitle>
                      <p className="max-w-3xl text-[15px] leading-7 text-muted-foreground">
                        {phase.description}
                      </p>
                    </div>

                    <Button asChild variant="outline" size="lg" className="h-11 px-5 text-base">
                      <Link to={`/app/roadmap/${phase.id}`}>
                        View Details
                        <RiArrowRightLine className="h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    {roadmapSections.map((section) => {
                      const meta = sectionMeta[section.key];
                      const count = phase.topics[`${section.key}_topics` as const]?.length ?? 0;

                      return (
                        <div
                          key={`${phase.id}-${section.key}`}
                          className="flex items-center gap-4 border border-border bg-background px-4 py-4"
                        >
                          <div
                            className={cn(
                              "flex h-11 w-11 items-center justify-center border",
                              meta.bg,
                              meta.border
                            )}
                          >
                            <section.icon className={cn("h-5 w-5", meta.color)} />
                          </div>
                          <div>
                            <div className="text-base font-semibold">{section.label}</div>
                            <div className="text-sm text-muted-foreground">{count} detailed items</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {phase.topics.study_plan_notes && (
                    <div className="border border-border bg-muted/20 p-4 text-[15px] leading-7 text-foreground/85">
                      {phase.topics.study_plan_notes}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
      </div>
    </div>
  );
}
