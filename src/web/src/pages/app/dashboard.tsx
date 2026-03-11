import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  RiArrowRightLine,
  RiBarChartLine,
  RiBookOpenLine,
  RiCalendarLine,
  RiEdit2Line,
  RiFlashlightLine,
  RiHeadphoneLine,
  RiLoader4Line,
  RiMicLine,
  RiStarLine,
  RiTrophyLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { getProgress, getDailyPlan, type ProgressOverview, type DailyStudyPlan } from "@/lib/ielts-api";
import { useAuth } from "@/lib/auth";
import { useOnboardingGate } from "./layout";

const sectionMeta: Record<string, { icon: typeof RiMicLine; color: string; bg: string }> = {
  listening: { icon: RiHeadphoneLine, color: "text-blue-600", bg: "bg-blue-500/10" },
  reading: { icon: RiBookOpenLine, color: "text-emerald-600", bg: "bg-emerald-500/10" },
  writing: { icon: RiEdit2Line, color: "text-amber-600", bg: "bg-amber-500/10" },
  speaking: { icon: RiMicLine, color: "text-purple-600", bg: "bg-purple-500/10" },
  vocabulary: { icon: RiFlashlightLine, color: "text-pink-600", bg: "bg-pink-500/10" },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { requireOnboarding } = useOnboardingGate();
  const navigate = useNavigate();
  const userId = user?.id;
  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [dailyPlan, setDailyPlan] = useState<DailyStudyPlan | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) return;
    const currentUserId = userId;
    async function load() {
      try {
        const [p, d] = await Promise.all([
          getProgress(currentUserId).catch(() => null),
          getDailyPlan(currentUserId).catch(() => null),
        ]);
        setProgress(p);
        setDailyPlan(d);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [userId]);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <RiLoader4Line className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const currentBand = progress?.current_estimated_band ?? 0;
  const targetBand = progress?.target_band_score ?? 7.0;
  const daysLeft = progress?.days_until_exam;
  const sectionScores = progress?.section_scores ?? {};

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      {/* Hero Stats */}
      <div className="mb-8 grid gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <RiStarLine className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Current Band</div>
              <div className="text-2xl font-bold">{currentBand || "—"}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
              <RiTrophyLine className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Target Band</div>
              <div className="text-2xl font-bold">{targetBand}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
              <RiCalendarLine className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Days Left</div>
              <div className="text-2xl font-bold">
                {daysLeft != null ? daysLeft : "—"}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
              <RiBarChartLine className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Tests Taken</div>
              <div className="text-2xl font-bold">
                {progress?.total_tests_taken ?? 0}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column: Section Scores + Actions */}
        <div className="space-y-6 lg:col-span-2">
          {/* Section Scores */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Section Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                {(["listening", "reading", "writing", "speaking"] as const).map(
                  (section) => {
                    const meta = sectionMeta[section];
                    const score = sectionScores[section] ?? 0;
                    const pct = (score / 9) * 100;

                    return (
                      <div
                        key={section}
                        className="flex items-center gap-3 rounded-lg border border-border/50 p-3"
                      >
                        <div
                          className={cn(
                            "flex h-9 w-9 items-center justify-center rounded-lg",
                            meta.bg
                          )}
                        >
                          <meta.icon className={cn("h-4 w-4", meta.color)} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-medium capitalize">
                              {section}
                            </span>
                            <span className="font-semibold">{score || "—"}</span>
                          </div>
                          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all",
                                score >= 7
                                  ? "bg-emerald-500"
                                  : score >= 5.5
                                    ? "bg-amber-500"
                                    : "bg-red-400"
                              )}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Practice</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                {(
                  [
                    { section: "listening", label: "Listening Practice" },
                    { section: "reading", label: "Reading Practice" },
                    { section: "writing", label: "Writing Practice" },
                    { section: "speaking", label: "Speaking Practice" },
                  ] as const
                ).map((item) => {
                  const meta = sectionMeta[item.section];
                  return (
                    <Button
                      key={item.section}
                      variant="outline"
                      className="h-auto w-full justify-start gap-3 p-3"
                      onClick={() => {
                        if (!requireOnboarding()) {
                          navigate(`/app/mock-test?section=${item.section}`);
                        }
                      }}
                    >
                      <div
                        className={cn(
                          "flex h-8 w-8 items-center justify-center rounded-lg",
                          meta.bg
                        )}
                      >
                        <meta.icon className={cn("h-4 w-4", meta.color)} />
                      </div>
                      <div className="text-left">
                        <div className="text-sm font-medium">
                          {item.label}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          AI-generated questions
                        </div>
                      </div>
                      <RiArrowRightLine className="ml-auto h-4 w-4 text-muted-foreground" />
                    </Button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Daily Plan + Strengths/Weaknesses */}
        <div className="space-y-6">
          {/* Daily Study Plan */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Today's Study Plan</CardTitle>
              {dailyPlan && (
                <Badge variant="secondary" className="text-xs">
                  {dailyPlan.completed_count}/{dailyPlan.total_count}
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              {dailyPlan && dailyPlan.activities.length > 0 ? (
                <div className="space-y-2">
                  {dailyPlan.activities.map((activity) => {
                    const meta =
                      sectionMeta[activity.section] || sectionMeta.vocabulary;
                    return (
                      <Link
                        key={activity.id}
                        to={dailyPlan ? `/app/daily-study/${dailyPlan.id}` : "/app/daily-study"}
                      >
                        <div
                          className={cn(
                            "flex items-center gap-3 rounded-lg border border-border/50 p-2.5 transition-colors hover:bg-accent",
                            activity.is_completed && "opacity-50"
                          )}
                        >
                          <div
                            className={cn(
                              "flex h-7 w-7 items-center justify-center rounded",
                              meta.bg
                            )}
                          >
                            <meta.icon className={cn("h-3.5 w-3.5", meta.color)} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="truncate text-sm font-medium">
                              {activity.title}
                            </div>
                            <div className="text-xs capitalize text-muted-foreground">
                              {activity.section}
                            </div>
                          </div>
                          {activity.is_completed && (
                            <Badge variant="secondary" className="text-xs text-emerald-600">
                              Done
                            </Badge>
                          )}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              ) : (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No activities available yet. Complete the placement test to get started.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Strengths & Weaknesses */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Your Profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {progress?.strengths && progress.strengths.length > 0 && (
                <div>
                  <div className="mb-1.5 text-xs font-medium text-emerald-600">
                    Strengths
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {progress.strengths.map((s, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {progress?.weaknesses && progress.weaknesses.length > 0 && (
                <div>
                  <div className="mb-1.5 text-xs font-medium text-amber-600">
                    Needs Work
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {progress.weaknesses.map((w, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {w}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {progress?.recommendations &&
                progress.recommendations.length > 0 && (
                  <div>
                    <div className="mb-1.5 text-xs font-medium text-blue-600">
                      Recommendations
                    </div>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {progress.recommendations.map((r, i) => (
                        <li key={i} className="flex gap-1.5">
                          <RiArrowRightLine className="mt-0.5 h-3 w-3 shrink-0 text-blue-500" />
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
