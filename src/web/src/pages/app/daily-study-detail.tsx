import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  RiArrowLeftLine,
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

const sectionMeta: Record<string, { icon: typeof RiMicLine; color: string; bg: string; border: string }> = {
  listening: { icon: RiHeadphoneLine, color: "text-blue-700", bg: "bg-blue-100", border: "border-blue-200" },
  reading: { icon: RiBookOpenLine, color: "text-emerald-700", bg: "bg-emerald-100", border: "border-emerald-200" },
  writing: { icon: RiEdit2Line, color: "text-amber-700", bg: "bg-amber-100", border: "border-amber-200" },
  speaking: { icon: RiMicLine, color: "text-violet-700", bg: "bg-violet-100", border: "border-violet-200" },
  vocabulary: { icon: RiFlashlightLine, color: "text-rose-700", bg: "bg-rose-100", border: "border-rose-200" },
};

type ContentRecord = Record<string, unknown>;

type CompletionState = {
  message: string;
  next_steps: string[];
  saved_response: boolean;
} | null;

function isContentRecord(value: unknown): value is ContentRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseContent(raw: unknown): ContentRecord {
  if (isContentRecord(raw)) return raw;

  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (!trimmed) return {};

    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        const parsed = JSON.parse(trimmed);
        return isContentRecord(parsed) ? parsed : { material: raw };
      } catch {
        return { material: raw };
      }
    }

    return { material: raw };
  }

  if (Array.isArray(raw)) {
    return { material: raw };
  }

  return {};
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
}

function asObjectArray(value: unknown): ContentRecord[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isContentRecord);
}

function renderRichText(value: unknown) {
  if (value == null) return null;

  if (typeof value === "string") {
    return <p className="whitespace-pre-wrap text-[15px] leading-7 text-foreground/90">{value}</p>;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return <p className="text-[15px] leading-7 text-foreground/90">{String(value)}</p>;
  }

  if (Array.isArray(value)) {
    const items = value.map((item) => (typeof item === "string" ? item : JSON.stringify(item)));
    return (
      <ul className="space-y-2">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="flex gap-3 text-[15px] leading-7 text-foreground/90">
            <RiArrowRightLine className="mt-1 h-4 w-4 shrink-0 text-primary" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    );
  }

  if (isContentRecord(value)) {
    return (
      <div className="space-y-3">
        {Object.entries(value).map(([key, child]) => (
          <div key={key} className="border border-border bg-background p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              {key.replace(/_/g, " ")}
            </p>
            <div className="mt-2">{renderRichText(child)}</div>
          </div>
        ))}
      </div>
    );
  }

  return <p className="text-[15px] leading-7 text-foreground/90">{String(value)}</p>;
}

function DetailBlock({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-3 border border-border bg-background p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {title}
      </p>
      {children}
    </div>
  );
}

function VocabularyGrid({ items }: { items: ContentRecord[] }) {
  if (items.length === 0) return null;

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {items.map((item, index) => (
        <div key={`vocab-${index}`} className="border border-border bg-background p-4">
          <p className="text-base font-semibold">{typeof item.word === "string" ? item.word : `Word ${index + 1}`}</p>
          {typeof item.meaning === "string" && (
            <p className="mt-1 text-[15px] leading-7 text-foreground/85">{item.meaning}</p>
          )}
          {typeof item.example === "string" && (
            <p className="mt-2 text-sm italic leading-6 text-muted-foreground">{item.example}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function QuestionList({ items }: { items: ContentRecord[] }) {
  if (items.length === 0) return null;

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={`question-${index}`} className="border border-border bg-background p-4">
          <p className="text-base font-semibold">
            {index + 1}. {typeof item.prompt === "string" ? item.prompt : "Practice question"}
          </p>
          {typeof item.answer_hint === "string" && (
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Hint: {item.answer_hint}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function ActivityContent({ activity }: { activity: StudyActivity }) {
  const content = parseContent(activity.content);
  const instructions = asStringArray(content.instructions);
  const sentenceFrames = asStringArray(content.sentence_frames);
  const checkpoints = asStringArray(content.checkpoints);
  const vocabulary = asObjectArray(content.vocabulary);
  const questions = asObjectArray(content.questions);

  const knownKeys = new Set([
    "overview",
    "instructions",
    "study_goal",
    "warm_up",
    "material_title",
    "material",
    "vocabulary",
    "questions",
    "sentence_frames",
    "checkpoints",
    "sample_response",
    "study_tip",
    "next_step",
  ]);

  const extraEntries = Object.entries(content).filter(([key]) => !knownKeys.has(key));

  return (
    <div className="space-y-5">
      {typeof content.overview === "string" && (
        <div className="border border-primary/20 bg-primary/5 p-5">
          <p className="text-lg leading-8 text-foreground/90">{content.overview}</p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {typeof content.study_goal === "string" && (
          <DetailBlock title="Study Goal">
            <p className="text-[15px] leading-7 text-foreground/90">{content.study_goal}</p>
          </DetailBlock>
        )}
        {typeof content.warm_up === "string" && (
          <DetailBlock title="Warm Up">
            <p className="text-[15px] leading-7 text-foreground/90">{content.warm_up}</p>
          </DetailBlock>
        )}
      </div>

      {instructions.length > 0 && (
        <DetailBlock title="Instructions">
          <ul className="space-y-2">
            {instructions.map((item, index) => (
              <li key={`${item}-${index}`} className="flex gap-3 text-[15px] leading-7 text-foreground/90">
                <span className="mt-1 inline-flex h-6 w-6 shrink-0 items-center justify-center border border-border bg-muted text-sm font-semibold">
                  {index + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </DetailBlock>
      )}

      <DetailBlock title={typeof content.material_title === "string" ? content.material_title : "Study Material"}>
        {renderRichText(content.material)}
      </DetailBlock>

      {vocabulary.length > 0 && (
        <DetailBlock title="Vocabulary Support">
          <VocabularyGrid items={vocabulary} />
        </DetailBlock>
      )}

      {questions.length > 0 && (
        <DetailBlock title="Practice Questions">
          <QuestionList items={questions} />
        </DetailBlock>
      )}

      {sentenceFrames.length > 0 && (
        <DetailBlock title="Sentence Frames">
          <div className="space-y-2">
            {sentenceFrames.map((frame, index) => (
              <div key={`${frame}-${index}`} className="border border-border bg-muted/20 px-4 py-3 text-[15px] leading-7 text-foreground/90">
                {frame}
              </div>
            ))}
          </div>
        </DetailBlock>
      )}

      {typeof content.sample_response === "string" && (
        <DetailBlock title="Sample Response">
          <p className="whitespace-pre-wrap text-[15px] leading-7 text-foreground/90">
            {content.sample_response}
          </p>
        </DetailBlock>
      )}

      {checkpoints.length > 0 && (
        <DetailBlock title="Checkpoints">
          <ul className="space-y-2">
            {checkpoints.map((item, index) => (
              <li key={`${item}-${index}`} className="flex gap-3 text-[15px] leading-7 text-foreground/90">
                <RiCheckLine className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </DetailBlock>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {typeof content.study_tip === "string" && (
          <DetailBlock title="Study Tip">
            <p className="text-[15px] leading-7 text-foreground/90">{content.study_tip}</p>
          </DetailBlock>
        )}
        {typeof content.next_step === "string" && (
          <DetailBlock title="Next Step">
            <p className="text-[15px] leading-7 text-foreground/90">{content.next_step}</p>
          </DetailBlock>
        )}
      </div>

      {extraEntries.length > 0 && (
        <DetailBlock title="More Details">
          <div className="space-y-4">
            {extraEntries.map(([key, value]) => (
              <div key={key} className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  {key.replace(/_/g, " ")}
                </p>
                {renderRichText(value)}
              </div>
            ))}
          </div>
        </DetailBlock>
      )}
    </div>
  );
}

function getResponsePlaceholder(section: string) {
  switch (section) {
    case "writing":
      return "Write your sentences here. Keep them short and clear.";
    case "speaking":
      return "Write what you would say, or make quick speaking notes here.";
    case "reading":
      return "Write your answers or a short summary of what you understood.";
    case "listening":
      return "Write the main details you heard or your answers to the questions.";
    default:
      return "Write your notes, answers, or example sentences here.";
  }
}

function updateCompletedPlan(plan: DailyStudyPlan, activityId: string): DailyStudyPlan {
  const alreadyCompleted = plan.activities.find((activity) => activity.id === activityId)?.is_completed;
  const activities = plan.activities.map((activity) =>
    activity.id === activityId ? { ...activity, is_completed: true } : activity
  );
  const completedCount = alreadyCompleted ? plan.completed_count : Math.min(plan.completed_count + 1, plan.total_count);

  return {
    ...plan,
    activities,
    completed_count: completedCount,
    is_completed: completedCount >= plan.total_count,
  };
}

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
  const [completion, setCompletion] = useState<CompletionState>(null);

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
    if (!plan) return;

    const nextSelected =
      (activityIdParam && plan.activities.find((activity) => activity.id === activityIdParam)) ||
      plan.activities[0] ||
      null;

    setSelectedActivity(nextSelected);
  }, [plan, activityIdParam]);

  const progressWidth = useMemo(() => {
    if (!plan || plan.total_count === 0) return 0;
    return Math.round((plan.completed_count / plan.total_count) * 100);
  }, [plan]);

  async function saveResponse(text: string) {
    if (!selectedActivity || !text.trim()) return;

    setSubmitting(true);
    try {
      const result = await submitActivityResponse(selectedActivity.id, text.trim());
      setCompletion(result);
      setPlan((current) => (current ? updateCompletedPlan(current, selectedActivity.id) : current));
      toast.success("Your work has been saved.");
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

  async function handleSubmitResponse() {
    await saveResponse(response);
  }

  async function handleQuickComplete() {
    if (!selectedActivity) return;
    setQuickCompleting(true);
    try {
      const result = await submitActivityResponse(selectedActivity.id, response.trim() || "Completed.");
      setCompletion(result);
      setPlan((current) => (current ? updateCompletedPlan(current, selectedActivity.id) : current));
      toast.success("Activity marked as complete.");
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
      <div className="mx-auto max-w-4xl px-6 py-8">
        <Card className="border border-border shadow-none">
          <CardContent className="py-16 text-center text-lg text-muted-foreground">
            Plan not found.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-8 space-y-4 border-b border-border pb-6">
        <Link to="/app/daily-study" className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground">
          <RiArrowLeftLine className="h-4 w-4" />
          Back to daily study
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={plan.is_completed ? "default" : "secondary"} className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
                {plan.is_completed ? "Completed" : "In Progress"}
              </Badge>
              <span className="text-sm text-muted-foreground">{plan.completed_count}/{plan.total_count} activities done</span>
            </div>
            <h1 className="text-4xl font-semibold tracking-tight">{plan.study_date}</h1>
            {plan.ai_rationale && (
              <p className="max-w-4xl text-lg leading-8 text-muted-foreground">{plan.ai_rationale}</p>
            )}
          </div>

          <div className="min-w-[240px] border border-border bg-muted/20 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Progress
            </p>
            <p className="mt-2 text-3xl font-semibold">{progressWidth}%</p>
            <div className="mt-3 h-3 overflow-hidden border border-border bg-background">
              <div className="h-full bg-primary transition-all" style={{ width: `${progressWidth}%` }} />
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="space-y-3">
          {plan.activities.map((activity, index) => {
            const meta = sectionMeta[activity.section] || sectionMeta.vocabulary;
            const isSelected = selectedActivity?.id === activity.id;

            return (
              <button
                key={activity.id}
                onClick={() => {
                  setSelectedActivity(activity);
                  setResponse("");
                  setCompletion(null);
                }}
                className={cn(
                  "w-full border bg-card px-4 py-4 text-left transition-colors",
                  isSelected ? "border-primary bg-primary/5" : "border-border hover:border-primary/30 hover:bg-accent/10"
                )}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      "flex h-11 w-11 items-center justify-center border",
                      meta.bg,
                      meta.border
                    )}
                  >
                    <meta.icon className={cn("h-5 w-5", meta.color)} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Activity {index + 1}
                      </span>
                      {activity.is_completed && (
                        <Badge variant="secondary" className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]">
                          Done
                        </Badge>
                      )}
                    </div>
                    <p className="mt-2 text-base font-semibold leading-6">{activity.title}</p>
                    <p className="mt-1 text-sm capitalize text-muted-foreground">
                      {activity.section.replace("_", " ")}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div>
          {selectedActivity ? (
            <Card className="border border-border shadow-none">
              <CardContent className="space-y-6 p-6 lg:p-8">
                <div className="space-y-3 border-b border-border pb-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
                      {selectedActivity.section.replace("_", " ")}
                    </Badge>
                    <Badge variant="secondary" className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em]">
                      {selectedActivity.activity_type.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <h2 className="text-3xl font-semibold tracking-tight">{selectedActivity.title}</h2>
                </div>

                <ActivityContent activity={selectedActivity} />

                {completion ? (
                  <div className="space-y-4 border border-emerald-200 bg-emerald-50/70 p-5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center border border-emerald-200 bg-white">
                        <RiCheckLine className="h-5 w-5 text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-lg font-semibold text-emerald-800">Activity saved</p>
                        <p className="text-sm text-emerald-700">{completion.message}</p>
                      </div>
                    </div>
                    {completion.next_steps.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                          Next Steps
                        </p>
                        <ul className="space-y-2">
                          {completion.next_steps.map((step, index) => (
                            <li key={`${step}-${index}`} className="flex gap-3 text-[15px] leading-7 text-emerald-900">
                              <RiArrowRightLine className="mt-1 h-4 w-4 shrink-0 text-emerald-700" />
                              <span>{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : selectedActivity.is_completed ? (
                  <div className="flex items-center gap-3 border border-emerald-200 bg-emerald-50/70 p-4 text-base font-medium text-emerald-800">
                    <RiCheckLine className="h-5 w-5" />
                    This activity is already completed.
                  </div>
                ) : (
                  <div className="space-y-4 border-t border-border pt-6">
                    <div className="space-y-2">
                      <p className="text-lg font-semibold">Write your work</p>
                      <p className="text-sm leading-6 text-muted-foreground">
                        You can write full answers, short notes, or sentence practice here. This phase saves progress and does not score you.
                      </p>
                    </div>

                    <Textarea
                      value={response}
                      onChange={(e) => setResponse(e.target.value)}
                      placeholder={getResponsePlaceholder(selectedActivity.section)}
                      className="min-h-[180px] resize-y border-border bg-background px-4 py-3 text-[15px] leading-7 shadow-none"
                    />

                    <div className="flex flex-col gap-3 sm:flex-row">
                      <Button
                        onClick={handleSubmitResponse}
                        disabled={!response.trim() || submitting}
                        className="h-12 flex-1 text-base"
                      >
                        {submitting ? (
                          <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <RiSendPlane2Line className="mr-2 h-4 w-4" />
                        )}
                        Save My Work
                      </Button>
                      <Button
                        onClick={handleQuickComplete}
                        disabled={quickCompleting || submitting}
                        variant="outline"
                        className="h-12 px-5 text-base"
                      >
                        {quickCompleting && <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" />}
                        Mark Complete
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-border shadow-none">
              <CardContent className="py-16 text-center text-lg text-muted-foreground">
                Select an activity to begin.
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
