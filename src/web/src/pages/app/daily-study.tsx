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
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Daily Study</h1>
          <p className="text-sm text-muted-foreground">
            Review the last 7 days of plans and generate today's study.
          </p>
        </div>
        {!todaysPlan && (
          <Button onClick={handleGenerate} disabled={generating}>
            {generating ? (
              <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RiCheckLine className="mr-2 h-4 w-4" />
            )}
            Generate Today
          </Button>
        )}
      </div>

      <div className="space-y-4">
        {plans.length > 0 ? (
          plans.map((plan) => (
            <Card key={plan.id}>
              <CardHeader className="flex flex-row items-start justify-between gap-4">
                <div>
                  <CardTitle className="text-base">
                    {plan.study_date === todayKey ? "Today" : plan.study_date}
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    {plan.completed_count}/{plan.total_count} completed
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {plan.study_date === todayKey && (
                    <Badge variant="default" className="text-xs">Today</Badge>
                  )}
                  <Badge variant={plan.is_completed ? "default" : "secondary"} className="text-xs">
                    {plan.is_completed ? "Completed" : "In progress"}
                  </Badge>
                  <Button size="sm" variant="outline" asChild>
                    <Link to={`/app/daily-study/${plan.id}`}>
                      Details
                      <RiArrowRightLine className="ml-2 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {plan.ai_rationale && (
                  <p className="text-sm text-muted-foreground">{plan.ai_rationale}</p>
                )}
                <div className="space-y-3">
                  <div className="grid gap-2 sm:grid-cols-2">
                    {plan.activities.slice(0, 4).map((activity) => {
                      const meta = sectionMeta[activity.section] || sectionMeta.vocabulary;
                      return (
                        <Link
                          key={activity.id}
                          to={`/app/daily-study/${plan.id}?activityId=${activity.id}`}
                          className={cn(
                            "flex items-center gap-3 rounded-lg border border-border/50 p-2.5 transition-all hover:border-primary/50 hover:bg-accent/30",
                            activity.is_completed && "opacity-60"
                          )}
                        >
                          <div className={cn("flex h-8 w-8 items-center justify-center rounded-md", meta.bg)}>
                            <meta.icon className={cn("h-4 w-4", meta.color)} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-medium">{activity.title}</div>
                            <div className="text-xs capitalize text-muted-foreground">
                              {activity.section}
                            </div>
                          </div>
                          <RiArrowRightLine className="h-3 w-3 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                        </Link>
                      );
                    })}
                  </div>
                  {plan.activities.length > 4 && (
                    <Button variant="ghost" size="sm" className="w-full text-xs text-muted-foreground hover:text-primary" asChild>
                      <Link to={`/app/daily-study/${plan.id}`}>
                        View all {plan.activities.length} activities
                        <RiArrowRightLine className="ml-1 h-3 w-3" />
                      </Link>
                    </Button>
                  )}
                </div>

              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                No study plans yet. Generate today's plan to get started.
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
            >
              {hasMore ? "Load previous 7 days" : "No more plans"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
