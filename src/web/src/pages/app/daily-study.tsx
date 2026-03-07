import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  getDailyPlan,
  submitActivityResponse,
  type DailyStudyPlan,
  type StudyActivity,
} from "@/lib/ielts-api";

const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

const sectionMeta: Record<string, { icon: typeof RiMicLine; color: string; bg: string }> = {
  listening: { icon: RiHeadphoneLine, color: "text-blue-600", bg: "bg-blue-500/10" },
  reading: { icon: RiBookOpenLine, color: "text-emerald-600", bg: "bg-emerald-500/10" },
  writing: { icon: RiEdit2Line, color: "text-amber-600", bg: "bg-amber-500/10" },
  speaking: { icon: RiMicLine, color: "text-purple-600", bg: "bg-purple-500/10" },
  vocabulary: { icon: RiFlashlightLine, color: "text-pink-600", bg: "bg-pink-500/10" },
};

export default function DailyStudyPage() {
  const [plan, setPlan] = useState<DailyStudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedActivity, setSelectedActivity] = useState<StudyActivity | null>(null);
  const [response, setResponse] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{
    band_score: number | null;
    suggestions: string[];
    is_correct: boolean | null;
  } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const p = await getDailyPlan(DEMO_USER_ID);
        setPlan(p);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

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
      // Mark completed locally
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
    } finally {
      setSubmitting(false);
    }
  }

  function handleBackToList() {
    setSelectedActivity(null);
    setResponse("");
    setFeedback(null);
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <RiLoader4Line className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // ── Activity Detail View ──────────────────────────────────────
  if (selectedActivity) {
    const meta = sectionMeta[selectedActivity.section] || sectionMeta.vocabulary;

    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        <button
          onClick={handleBackToList}
          className="mb-4 text-sm text-muted-foreground hover:text-foreground"
        >
          &larr; Back to plan
        </button>

        <div className="mb-4 flex items-center gap-3">
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", meta.bg)}>
            <meta.icon className={cn("h-5 w-5", meta.color)} />
          </div>
          <div>
            <h2 className="text-lg font-bold">{selectedActivity.title}</h2>
            <span className="text-xs capitalize text-muted-foreground">
              {selectedActivity.section} · {selectedActivity.activity_type}
            </span>
          </div>
        </div>

        {/* Activity Content */}
        <Card className="mb-4">
          <CardContent className="prose prose-sm dark:prose-invert pt-4">
            {"instructions" in selectedActivity.content && (
              <p>{String(selectedActivity.content.instructions)}</p>
            )}
            {"prompt" in selectedActivity.content && (
              <p className="font-medium">{String(selectedActivity.content.prompt)}</p>
            )}
            {"passage" in selectedActivity.content && (
              <blockquote className="text-sm">{String(selectedActivity.content.passage)}</blockquote>
            )}
            {Array.isArray(selectedActivity.content.options) && (
              <ul>
                {(selectedActivity.content.options as string[]).map((opt, i) => (
                  <li key={i}>{opt}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Feedback Display */}
        {feedback ? (
          <Card className="mb-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <RiCheckLine className="h-4 w-4 text-emerald-500" />
                Feedback
                {feedback.band_score != null && (
                  <Badge variant="secondary" className="ml-auto text-xs">
                    Band {feedback.band_score}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {feedback.is_correct != null && (
                <p className={cn("mb-2 text-sm font-medium", feedback.is_correct ? "text-emerald-600" : "text-amber-600")}>
                  {feedback.is_correct ? "Correct!" : "Not quite right."}
                </p>
              )}
              {feedback.suggestions.length > 0 && (
                <ul className="space-y-1">
                  {feedback.suggestions.map((s, i) => (
                    <li key={i} className="flex gap-2 text-sm">
                      <RiArrowRightLine className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-500" />
                      {s}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        ) : selectedActivity.is_completed ? (
          <Card className="mb-4">
            <CardContent className="flex items-center gap-2 py-4 text-sm text-emerald-600">
              <RiCheckLine className="h-4 w-4" />
              Activity already completed.
            </CardContent>
          </Card>
        ) : (
          <>
            <Textarea
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              placeholder="Type your answer here…"
              className="mb-3 min-h-30 resize-none"
            />
            <Button
              onClick={handleSubmitResponse}
              disabled={!response.trim() || submitting}
              className="w-full"
            >
              {submitting ? (
                <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RiSendPlane2Line className="mr-2 h-4 w-4" />
              )}
              Submit Response
            </Button>
          </>
        )}
      </div>
    );
  }

  // ── Plan List View ────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Daily Study</h1>
          <p className="text-sm text-muted-foreground">
            {plan ? `${plan.study_date} · ${plan.completed_count}/${plan.total_count} completed` : "No plan available"}
          </p>
        </div>
        {plan && (
          <Badge variant={plan.is_completed ? "default" : "secondary"}>
            {plan.is_completed ? "All done!" : `${plan.total_count - plan.completed_count} remaining`}
          </Badge>
        )}
      </div>

      {plan && plan.ai_rationale && (
        <Card className="mb-4">
          <CardContent className="py-3 text-sm text-muted-foreground">
            {plan.ai_rationale}
          </CardContent>
        </Card>
      )}

      {plan && plan.activities.length > 0 ? (
        <div className="space-y-2">
          {plan.activities.map((activity) => {
            const meta = sectionMeta[activity.section] || sectionMeta.vocabulary;
            return (
              <button
                key={activity.id}
                onClick={() => setSelectedActivity(activity)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-all hover:bg-accent",
                  activity.is_completed && "opacity-60"
                )}
              >
                <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", meta.bg)}>
                  <meta.icon className={cn("h-5 w-5", meta.color)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{activity.title}</div>
                  <div className="text-xs capitalize text-muted-foreground">
                    {activity.section} · {activity.activity_type}
                  </div>
                </div>
                {activity.is_completed ? (
                  <Badge variant="secondary" className="text-xs text-emerald-600">
                    <RiCheckLine className="mr-1 h-3 w-3" />
                    Done
                  </Badge>
                ) : (
                  <RiArrowRightLine className="h-4 w-4 text-muted-foreground" />
                )}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="py-16 text-center">
          <p className="text-muted-foreground">
            No study plan available yet. Complete the placement test to get a personalized plan.
          </p>
        </div>
      )}
    </div>
  );
}
