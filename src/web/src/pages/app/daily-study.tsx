import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  RiArrowRightLine,
  RiBookOpenLine,
  RiCheckLine,
  RiEdit2Line,
  RiFlashlightLine,
  RiHeadphoneLine,
  RiLoader4Line,
  RiMicLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import {
  generateDailyPlan,
  getDailyPlanHistory,
  type DailyStudyPlan,
} from "@/lib/ielts-api";
import { useAuth } from "@/lib/auth";
import { getUserFacingErrorMessage } from "@/lib/app-errors";
import { toast } from "sonner";

const sectionMeta: Record<string, { icon: typeof RiMicLine; color: string; bg: string }> = {
  listening: { icon: RiHeadphoneLine, color: "text-blue-600", bg: "bg-blue-500/10" },
  reading: { icon: RiBookOpenLine, color: "text-emerald-600", bg: "bg-emerald-500/10" },
  writing: { icon: RiEdit2Line, color: "text-amber-600", bg: "bg-amber-500/10" },
  speaking: { icon: RiMicLine, color: "text-purple-600", bg: "bg-purple-500/10" },
  vocabulary: { icon: RiFlashlightLine, color: "text-pink-600", bg: "bg-pink-500/10" },
};

export default function DailyStudyPage() {
  const { user } = useAuth();
  const userId = user?.id;
  const [plans, setPlans] = useState<DailyStudyPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [daysToLoad, setDaysToLoad] = useState(7);
  const [hasMore, setHasMore] = useState(true);
  const todayKey = useMemo(() => new Date().toISOString().slice(0, 10), []);

  useEffect(() => {
    if (!userId) return;
    const currentUserId = userId;
    async function load() {
      try {
        const response = await getDailyPlanHistory(currentUserId, daysToLoad);
        setPlans(response.items);
        setHasMore(response.items.length >= daysToLoad && daysToLoad < 365);
      } catch (e) {
        console.error(e);
        toast.error(
          getUserFacingErrorMessage(
            e,
            "Couldn't load your study plan. Please try again."
          )
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [userId, daysToLoad]);

  const todaysPlan = plans.find((p) => p.study_date === todayKey);

  async function handleGenerate() {
    if (!userId) return;
    setGenerating(true);
    try {
      const created = await generateDailyPlan(userId);
      setPlans((prev) => {
        const filtered = prev.filter((p) => p.id !== created.id);
        return [created, ...filtered];
      });
      toast.success("Today's plan is ready.");
    } catch (e) {
      console.error(e);
      toast.error(
        getUserFacingErrorMessage(
          e,
          "Couldn't generate your study plan. Please try again."
        )
      );
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <RiLoader4Line className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-3">
          <Badge variant="outline" className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]">
            Daily Study
          </Badge>
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">Daily Practice Plan</h1>
            <p className="mt-2 max-w-3xl text-lg leading-8 text-muted-foreground">
              Open a clear, beginner-friendly study set for each day. Plans focus on
              vocabulary, listening, reading, writing, and speaking without turning this
              practice phase into a test.
            </p>
          </div>
        </div>
        {!todaysPlan && (
          <Button onClick={handleGenerate} disabled={generating} className="h-12 px-6 text-base">
            {generating ? (
              <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RiCheckLine className="mr-2 h-4 w-4" />
            )}
            Generate Today
          </Button>
        )}
      </div>

      <div className="space-y-5">
        {plans.length > 0 ? (
          plans.map((plan) => (
            <Card key={plan.id} className="border border-border shadow-none">
              <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    {plan.study_date === todayKey && (
                      <Badge className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
                        Today
                      </Badge>
                    )}
                    <Badge variant={plan.is_completed ? "default" : "secondary"} className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
                      {plan.is_completed ? "Completed" : "In Progress"}
                    </Badge>
                  </div>
                  <CardTitle className="text-2xl font-semibold">
                    {plan.study_date === todayKey ? "Today's Study Plan" : plan.study_date}
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {plan.completed_count}/{plan.total_count} activities completed
                  </p>
                </div>
                <Button size="lg" variant="outline" asChild className="h-11 px-5 text-base">
                  <Link to={`/app/daily-study/${plan.id}`}>
                    Open Plan
                    <RiArrowRightLine className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent className="space-y-5">
                {plan.ai_rationale && (
                  <div className="border border-border bg-muted/20 p-4 text-[15px] leading-7 text-foreground/85">
                    {plan.ai_rationale}
                  </div>
                )}

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {plan.activities.map((activity) => {
                    const meta = sectionMeta[activity.section] || sectionMeta.vocabulary;
                    return (
                      <Link
                        key={activity.id}
                        to={`/app/daily-study/${plan.id}?activityId=${activity.id}`}
                        className={cn(
                          "group flex items-center gap-4 border border-border bg-background px-4 py-4 transition-colors hover:border-primary/40 hover:bg-accent/20",
                          activity.is_completed && "border-emerald-200 bg-emerald-50/40"
                        )}
                      >
                        <div className={cn("flex h-11 w-11 items-center justify-center border", meta.bg)}>
                          <meta.icon className={cn("h-5 w-5", meta.color)} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-base font-semibold">{activity.title}</div>
                          <div className="text-sm capitalize text-muted-foreground">
                            {activity.section.replace("_", " ")}
                          </div>
                        </div>
                        <RiArrowRightLine className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                      </Link>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card className="border border-border shadow-none">
            <CardContent className="py-16 text-center">
              <p className="text-lg text-muted-foreground">
                No study plans yet. Generate today&apos;s plan to get started.
              </p>
            </CardContent>
          </Card>
        )}

        {plans.length > 0 && (
          <div className="flex justify-center pt-2">
            <Button
              variant="outline"
              onClick={() => setDaysToLoad((prev) => Math.min(prev + 7, 365))}
              disabled={!hasMore}
              className="h-11 px-5 text-base"
            >
              {hasMore ? "Load Previous 7 Days" : "No More Plans"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
