import { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  RiTimeLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import {
  startMockTest,
  submitMockAnswer,
  type MockTestQuestion,
  type MockTestReport,
} from "@/lib/ielts-api";

const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

type Phase = "setup" | "test" | "report";

const sections = [
  { key: "listening", label: "Listening", icon: RiHeadphoneLine, color: "text-blue-600", bg: "bg-blue-500/10" },
  { key: "reading", label: "Reading", icon: RiBookOpenLine, color: "text-emerald-600", bg: "bg-emerald-500/10" },
  { key: "writing", label: "Writing", icon: RiEdit2Line, color: "text-amber-600", bg: "bg-amber-500/10" },
  { key: "speaking", label: "Speaking", icon: RiMicLine, color: "text-purple-600", bg: "bg-purple-500/10" },
  { key: "full", label: "Full Test", icon: RiFlashlightLine, color: "text-primary", bg: "bg-primary/10" },
] as const;

export default function MockTestPage() {
  const [searchParams] = useSearchParams();
  const initialSection = searchParams.get("section") || "";

  const [phase, setPhase] = useState<Phase>(initialSection ? "setup" : "setup");
  const [selectedSection, setSelectedSection] = useState(initialSection);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<MockTestQuestion | null>(null);
  const [report, setReport] = useState<MockTestReport | null>(null);
  const [answer, setAnswer] = useState("");

  async function handleStart() {
    setLoading(true);
    try {
      const q = await startMockTest(DEMO_USER_ID, {
        test_type: selectedSection === "full" ? "full" : "section",
        section: selectedSection === "full" ? undefined : selectedSection,
      });
      setQuestion(q);
      setPhase("test");
      setAnswer("");
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    if (!question || !answer.trim()) return;
    setLoading(true);
    try {
      const result = await submitMockAnswer(question.thread_id, answer.trim());
      if (result.status === "completed") {
        setReport(result as MockTestReport);
        setPhase("report");
      } else {
        setQuestion(result as MockTestQuestion);
        setAnswer("");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  // ── Setup Phase ───────────────────────────────────────────────
  if (phase === "setup") {
    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        <h1 className="mb-2 text-2xl font-bold tracking-tight">Mock Test</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Choose a section to practice or take a full test.
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          {sections.map((s) => (
            <button
              key={s.key}
              onClick={() => setSelectedSection(s.key)}
              className={cn(
                "flex items-center gap-3 rounded-xl border p-4 text-left transition-all",
                selectedSection === s.key
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "border-border/50 hover:border-border"
              )}
            >
              <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", s.bg)}>
                <s.icon className={cn("h-5 w-5", s.color)} />
              </div>
              <div>
                <div className="font-medium">{s.label}</div>
                <div className="text-xs text-muted-foreground">
                  {s.key === "full" ? "All 4 sections" : `${s.label} section only`}
                </div>
              </div>
            </button>
          ))}
        </div>

        <Button
          className="mt-6 w-full"
          size="lg"
          disabled={!selectedSection || loading}
          onClick={handleStart}
        >
          {loading ? (
            <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RiFlashlightLine className="mr-2 h-4 w-4" />
          )}
          Start Test
        </Button>
      </div>
    );
  }

  // ── Test Phase ────────────────────────────────────────────────
  if (phase === "test" && question) {
    const pct = ((question.question_index + 1) / question.total_questions) * 100;

    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        {/* Progress */}
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between text-sm">
            <Badge variant="secondary" className="capitalize">
              {question.section}
            </Badge>
            <span className="text-muted-foreground">
              Q{question.question_index + 1} / {question.total_questions}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Passage */}
        {question.passage && (
          <Card className="mb-4">
            <CardContent className="prose prose-sm dark:prose-invert max-h-60 overflow-y-auto pt-4 text-sm">
              <div dangerouslySetInnerHTML={{ __html: question.passage }} />
            </CardContent>
          </Card>
        )}

        {/* Question */}
        <Card className="mb-4">
          <CardContent className="pt-6">
            <p className="mb-4 text-sm leading-relaxed">{question.question_text}</p>

            {question.options && question.options.length > 0 ? (
              <div className="space-y-2">
                {question.options.map((opt, i) => (
                  <button
                    key={i}
                    onClick={() => setAnswer(opt)}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left text-sm transition-all",
                      answer === opt
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : "border-border/50 hover:border-border"
                    )}
                  >
                    <span className="mr-2 font-medium text-muted-foreground">
                      {String.fromCharCode(65 + i)}.
                    </span>
                    {opt}
                  </button>
                ))}
              </div>
            ) : (
              <Textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer here…"
                className="min-h-[120px] resize-none"
              />
            )}
          </CardContent>
        </Card>

        {/* Timer hint + Submit */}
        <div className="flex items-center justify-between">
          {question.time_limit_seconds ? (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <RiTimeLine className="h-3.5 w-3.5" />
              {Math.ceil(question.time_limit_seconds / 60)} min suggested
            </span>
          ) : (
            <span />
          )}
          <Button onClick={handleSubmit} disabled={!answer.trim() || loading}>
            {loading ? (
              <RiLoader4Line className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RiArrowRightLine className="mr-2 h-4 w-4" />
            )}
            Submit Answer
          </Button>
        </div>
      </div>
    );
  }

  // ── Report Phase ──────────────────────────────────────────────
  if (phase === "report" && report) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        <h1 className="mb-6 text-center text-2xl font-bold tracking-tight">
          Test Complete
        </h1>

        {/* Overall Band */}
        {report.overall_band != null && (
          <div className="mb-6 flex flex-col items-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
              <span className="text-3xl font-bold text-primary">
                {report.overall_band}
              </span>
            </div>
            <span className="mt-2 text-sm text-muted-foreground">
              Overall Band Score
            </span>
          </div>
        )}

        {/* Section Scores */}
        {report.section_scores.length > 0 && (
          <Card className="mb-4">
            <CardHeader>
              <CardTitle className="text-base">Section Scores</CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-border/50">
              {report.section_scores.map((s, i) => (
                <div key={i} className="flex items-center justify-between py-2 first:pt-0 last:pb-0">
                  <span className="text-sm capitalize">{s.section}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">{s.band_score}</span>
                    <span className="max-w-[180px] truncate text-xs text-muted-foreground">
                      {s.detail}
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Strengths & Weaknesses */}
        <div className="mb-4 grid gap-3 sm:grid-cols-2">
          {report.strengths.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-emerald-600">Strengths</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {report.strengths.map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <RiCheckLine className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
                      {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          {report.weaknesses.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-amber-600">Areas to Improve</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {report.weaknesses.map((w, i) => (
                    <li key={i} className="flex gap-2">
                      <RiArrowRightLine className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                      {w}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-sm text-blue-600">Recommendations</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm">
                {report.recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <RiFlashlightLine className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-500" />
                    {r}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        <div className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => {
              setPhase("setup");
              setReport(null);
              setQuestion(null);
              setAnswer("");
            }}
          >
            <RiArrowLeftLine className="mr-2 h-4 w-4" />
            Take Another Test
          </Button>
          <Link to="/app/dashboard" className="flex-1">
            <Button className="w-full">Go to Dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  return null;
}
