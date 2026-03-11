import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  RiArrowRightLine,
  RiBookOpenLine,
  RiCheckLine,
  RiEdit2Line,
  RiFlashlightLine,
  RiHeadphoneLine,
  RiLoader4Line,
  RiMicLine,
  RiSendPlane2Line,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import {
  getDailyPlanById,
  submitActivityResponse,
  type DailyStudyPlan,
  type StudyActivity,
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

export default function DailyStudyDetailPage() {
  const { planId } = useParams();
  const [searchParams] = useSearchParams();
  const activityIdParam = searchParams.get("activityId");
  const { user } = useAuth();
  const userId = user?.id;
  const [plan, setPlan] = useState<DailyStudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedActivity, setSelectedActivity] = useState<StudyActivity | null>(null);
  const [response, setResponse] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [quickCompleting, setQuickCompleting] = useState(false);
  const [feedback, setFeedback] = useState<{
    band_score: number | null;
    suggestions: string[];
    is_correct: boolean | null;
  } | null>(null);

  useEffect(() => {
    if (!planId || !userId) {
      setLoading(false);
      return;
    }
    async function load() {
      try {
        const result = await getDailyPlanById(userId as string, planId as string);
        setPlan(result);
      } catch (e) {
        console.error(e);
        toast.error(
          getUserFacingErrorMessage(
            e,
            "Couldn't load this study plan. Please try again."
          )
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [planId, userId]);

  useEffect(() => {
    if (plan && activityIdParam && !selectedActivity) {
      const activity = plan.activities.find((a) => a.id === activityIdParam);
      if (activity) {
        setSelectedActivity(activity);
      }
    }
  }, [plan, activityIdParam, selectedActivity]);

  async function handleSubmitResponse() {
    if (!selectedActivity || !response.trim()) return;
    setSubmitting(true);
    try {
      const result = await submitActivityResponse(selectedActivity.id, response.trim());
      setFeedback({
        band_score: result.band_score,
        suggestions: result.suggestions,
        is_correct: result.is_correct,
      });
      toast.success("Response submitted successfully.");
      if (plan) {
        setPlan({
          ...plan,
          completed_count: plan.completed_count + 1,
          activities: plan.activities.map((a) =>
            a.id === selectedActivity.id ? { ...a, is_completed: true } : a
          ),
        });
      }
    } catch (e) {
      console.error(e);
      toast.error(
        getUserFacingErrorMessage(
          e,
          "Couldn't submit your response. Please try again."
        )
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleQuickComplete() {
    if (!selectedActivity) return;
    setQuickCompleting(true);
    try {
      const result = await submitActivityResponse(selectedActivity.id, "Completed.");
      setFeedback({
        band_score: result.band_score,
        suggestions: result.suggestions,
        is_correct: result.is_correct,
      });
      toast.success("Marked as completed.");
      if (plan) {
        setPlan({
          ...plan,
          completed_count: plan.completed_count + 1,
          activities: plan.activities.map((a) =>
            a.id === selectedActivity.id ? { ...a, is_completed: true } : a
          ),
        });
      }
    } catch (e) {
      console.error(e);
      toast.error(
        getUserFacingErrorMessage(
          e,
          "Couldn't mark this activity as completed. Please try again."
        )
      );
    } finally {
      setQuickCompleting(false);
    }
  }



  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <RiLoader4Line className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8">
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Plan not found.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/app/daily-study" className="text-sm text-muted-foreground hover:text-foreground">
            &larr; Back to daily study
          </Link>
          <h1 className="mt-2 text-2xl font-bold tracking-tight">{plan.study_date}</h1>
          <p className="text-sm text-muted-foreground">
            {plan.completed_count}/{plan.total_count} completed
          </p>
          <div className="mt-2 h-2 w-48 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{
                width: `${plan.total_count > 0 ? Math.round((plan.completed_count / plan.total_count) * 100) : 0}%`,
              }}
            />
          </div>
        </div>
        <Badge variant={plan.is_completed ? "default" : "secondary"}>
          {plan.is_completed ? "Completed" : "In progress"}
        </Badge>
      </div>

      {plan.ai_rationale && (
        <Card className="mb-4">
          <CardContent className="py-3 text-sm text-muted-foreground">
            {plan.ai_rationale}
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {plan.activities.map((activity) => {
          const isSelected = selectedActivity?.id === activity.id;
          const meta = sectionMeta[activity.section] || sectionMeta.vocabulary;
          
          return (
            <div
              key={activity.id}
              className={cn(
                "overflow-hidden rounded-xl border transition-all",
                isSelected ? "border-primary ring-1 ring-primary/20" : "hover:border-primary/50 shadow-sm"
              )}
            >
              <button
                onClick={() => {
                  if (isSelected) {
                    setSelectedActivity(null);
                  } else {
                    setSelectedActivity(activity);
                    setFeedback(null);
                    setResponse("");
                  }
                }}
                className={cn(
                  "flex w-full items-center gap-3 p-4 text-left transition-all",
                  activity.is_completed && !isSelected && "opacity-60"
                )}
              >
                <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", meta.bg)}>
                  <meta.icon className={cn("h-5 w-5", meta.color)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{activity.title}</div>
                  <div className="text-xs capitalize text-muted-foreground">
                    {activity.section} - {activity.activity_type}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {activity.is_completed && (
                    <Badge variant="secondary" className="text-xs text-emerald-600 bg-emerald-500/10 border-emerald-500/20">
                      <RiCheckLine className="mr-1 h-3 w-3" />
                      Done
                    </Badge>
                  )}
                  <RiArrowRightLine className={cn("h-4 w-4 text-muted-foreground transition-transform", isSelected && "rotate-90")} />
                </div>
              </button>

              {isSelected && (
                <div className="border-t bg-muted/30 p-4 space-y-4">
                  <div className="prose prose-sm dark:prose-invert">
                    {"instructions" in activity.content && (
                      <p className="font-medium text-foreground">{String(activity.content.instructions)}</p>
                    )}
                    {"prompt" in activity.content && (
                      <p className="text-muted-foreground">{String(activity.content.prompt)}</p>
                    )}
                    {"material" in activity.content && typeof activity.content.material === "string" && (
                      <p className="text-muted-foreground">{activity.content.material}</p>
                    )}
                    {"material" in activity.content && Array.isArray(activity.content.material) && (
                      <ul className="list-disc pl-4 space-y-1">
                        {(activity.content.material as string[]).map((item, i) => (
                          <li key={i} className="text-muted-foreground">{item}</li>
                        ))}
                      </ul>
                    )}
                    {"passage" in activity.content && (
                      <blockquote className="border-l-2 pl-4 italic text-muted-foreground">
                        {String(activity.content.passage)}
                      </blockquote>
                    )}
                    {"questions" in activity.content && Array.isArray(activity.content.questions) && (
                      <ul className="list-decimal pl-4 space-y-2">
                        {(activity.content.questions as string[]).map((q, i) => (
                          <li key={i} className="text-foreground">{q}</li>
                        ))}
                      </ul>
                    )}
                    {Array.isArray(activity.content.options) && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                        {(activity.content.options as string[]).map((opt, i) => (
                          <div key={i} className="text-xs p-2 rounded border bg-background shadow-sm hover:border-primary/30 transition-colors uppercase tracking-tight">{opt}</div>
                        ))}
                      </div>
                    )}
                    {(!activity.content || Object.keys(activity.content).length === 0) && (
                      <p className="text-muted-foreground italic">No specific content details available.</p>
                    )}
                  </div>

                  {feedback ? (
                    <div className="rounded-lg border bg-background p-4 shadow-sm animate-in fade-in slide-in-from-top-2">
                      <div className="flex items-center gap-2 mb-3">
                        <RiCheckLine className="h-5 w-5 text-emerald-500" />
                        <span className="font-bold text-sm text-foreground">Feedback</span>
                        {feedback.band_score != null && (
                          <Badge variant="default" className="ml-auto">
                            Band {feedback.band_score}
                          </Badge>
                        )}
                      </div>
                      {feedback.is_correct != null && (
                        <p className={cn("mb-3 text-sm font-medium", feedback.is_correct ? "text-emerald-600" : "text-amber-600")}>
                          {feedback.is_correct ? "Great job! That's correct." : "Good effort! Let's review the suggestions below."}
                        </p>
                      )}
                      {feedback.suggestions.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Suggestions for improvement:</p>
                          <ul className="space-y-1.5">
                            {feedback.suggestions.map((s, i) => (
                              <li key={i} className="flex gap-2 text-sm leading-snug">
                                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                                {s}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : activity.is_completed ? (
                    <div className="flex items-center gap-2 py-2 text-sm text-emerald-600 font-medium">
                      <RiCheckLine className="h-4 w-4" />
                      Activity completed
                    </div>
                  ) : (
                    <div className="space-y-4 animate-in fade-in slide-in-from-top-1">
                      <Textarea
                        value={response}
                        onChange={(e) => setResponse(e.target.value)}
                        placeholder="Share your thoughts or answer here..."
                        className="min-h-[120px] resize-none bg-background shadow-sm border-muted-foreground/20 focus-visible:ring-primary/30"
                      />
                      <div className="flex flex-col sm:flex-row gap-3">
                        <Button
                          onClick={handleSubmitResponse}
                          disabled={!response.trim() || submitting}
                          className="flex-1 shadow-md transition-all active:scale-[0.98]"
                        >
                          {submitting ? <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" /> : <RiSendPlane2Line className="mr-2 h-4 w-4" />}
                          Submit Response
                        </Button>
                        <Button
                          onClick={handleQuickComplete}
                          disabled={quickCompleting || submitting}
                          variant="outline"
                          size="default"
                          className="sm:w-auto text-xs font-medium"
                        >
                          {quickCompleting && <RiLoader4Line className="mr-2 h-3.5 w-3.5 animate-spin" />}
                          Mark Done
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
