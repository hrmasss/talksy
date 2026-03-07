import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  RiArrowRightLine,
  RiArrowLeftLine,
  RiCheckLine,
  RiLoader4Line,
  RiHeadphoneLine,
  RiBookOpenLine,
  RiEdit2Line,
  RiMicLine,
  RiStarLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import {
  startPlacementTest,
  submitPlacementAnswer,
  type PlacementQuestion,
  type PlacementResult,
} from "@/lib/ielts-api";

const DEMO_USER_ID = "00000000-0000-0000-0000-000000000001";

const sectionIcons: Record<string, typeof RiHeadphoneLine> = {
  listening: RiHeadphoneLine,
  reading: RiBookOpenLine,
  writing: RiEdit2Line,
  speaking: RiMicLine,
};

const sectionColors: Record<string, string> = {
  listening: "bg-blue-500/10 text-blue-600",
  reading: "bg-emerald-500/10 text-emerald-600",
  writing: "bg-amber-500/10 text-amber-600",
  speaking: "bg-purple-500/10 text-purple-600",
};

type Phase = "setup" | "test" | "result";

export default function OnboardingPage() {
  const navigate = useNavigate();

  // Setup phase
  const [targetBand, setTargetBand] = useState(7.0);
  const [examDate, setExamDate] = useState("");

  // Test phase
  const [phase, setPhase] = useState<Phase>("setup");
  const [question, setQuestion] = useState<PlacementQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlacementResult | null>(null);

  const startTest = async () => {
    setLoading(true);
    try {
      const q = await startPlacementTest(DEMO_USER_ID, {
        target_band_score: targetBand,
        exam_date: examDate || undefined,
      });
      setQuestion(q);
      setPhase("test");
    } catch (err) {
      console.error("Failed to start placement test:", err);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!question || !answer.trim()) return;
    setLoading(true);
    try {
      const res = await submitPlacementAnswer(question.thread_id, answer.trim());
      setAnswer("");

      if (res.status === "completed") {
        setResult(res as PlacementResult);
        setPhase("result");
      } else {
        setQuestion(res as PlacementQuestion);
      }
    } catch (err) {
      console.error("Failed to submit answer:", err);
    } finally {
      setLoading(false);
    }
  };

  const goToDashboard = () => {
    navigate("/app");
  };

  // ── Setup Phase ──────────────────────────────────────────────
  if (phase === "setup") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="w-full max-w-lg">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <RiStarLine className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Welcome to IELTS Prep
            </h1>
            <p className="mt-2 text-muted-foreground">
              Let's start with a quick diagnostic test to understand your current
              level. This takes about 15 minutes.
            </p>
          </div>

          <Card>
            <CardContent className="space-y-6 pt-6">
              <div>
                <label className="mb-2 block text-sm font-medium">
                  Target Band Score
                </label>
                <div className="flex flex-wrap gap-2">
                  {[5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5].map((band) => (
                    <Button
                      key={band}
                      variant={targetBand === band ? "default" : "outline"}
                      size="sm"
                      onClick={() => setTargetBand(band)}
                    >
                      {band}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">
                  Exam Date (optional)
                </label>
                <Input
                  type="date"
                  value={examDate}
                  onChange={(e) => setExamDate(e.target.value)}
                  className="max-w-xs"
                />
              </div>

              <div className="rounded-lg border border-border/50 bg-muted/30 p-4">
                <h3 className="mb-3 text-sm font-medium">
                  What to expect
                </h3>
                <div className="space-y-2">
                  {["Listening", "Reading", "Writing", "Speaking"].map(
                    (section) => (
                      <div
                        key={section}
                        className="flex items-center gap-2 text-sm text-muted-foreground"
                      >
                        <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                        {section} — 2-3 questions, ~3 minutes
                      </div>
                    )
                  )}
                </div>
              </div>

              <Button
                className="w-full gap-2"
                size="lg"
                onClick={startTest}
                disabled={loading}
              >
                {loading ? (
                  <RiLoader4Line className="h-4 w-4 animate-spin" />
                ) : (
                  <RiArrowRightLine className="h-4 w-4" />
                )}
                Start Diagnostic Test
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // ── Test Phase ───────────────────────────────────────────────
  if (phase === "test" && question) {
    const SectionIcon =
      sectionIcons[question.section] || RiBookOpenLine;
    const progress =
      ((question.question_index + 1) / question.total_questions) * 100;

    return (
      <div className="flex min-h-screen flex-col bg-background">
        {/* Progress bar */}
        <div className="border-b border-border/50 bg-background/95 p-4">
          <div className="mx-auto max-w-2xl">
            <div className="mb-2 flex items-center justify-between text-sm">
              <Badge
                variant="secondary"
                className={cn("gap-1", sectionColors[question.section])}
              >
                <SectionIcon className="h-3 w-3" />
                {question.section.charAt(0).toUpperCase() +
                  question.section.slice(1)}
              </Badge>
              <span className="text-muted-foreground">
                {question.question_index + 1} / {question.total_questions}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Question */}
        <div className="flex flex-1 items-start justify-center p-6">
          <div className="w-full max-w-2xl">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg leading-relaxed">
                  {question.question_text.split("\n").map((line, i) => (
                    <span key={i}>
                      {line}
                      {i <
                        question.question_text.split("\n").length - 1 && <br />}
                    </span>
                  ))}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Options for MCQ */}
                {question.options.length > 0 ? (
                  <div className="space-y-2">
                    {question.options.map((opt, i) => (
                      <Button
                        key={i}
                        variant={answer === opt ? "default" : "outline"}
                        className="w-full justify-start text-left"
                        onClick={() => setAnswer(opt.charAt(0))}
                      >
                        {opt}
                      </Button>
                    ))}
                  </div>
                ) : (
                  <Textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder={
                      question.question_type === "essay"
                        ? "Write your response here (100-150 words)..."
                        : question.question_type === "speaking"
                          ? "Type your spoken response here..."
                          : "Type your answer..."
                    }
                    className="min-h-[120px]"
                  />
                )}

                <div className="flex justify-between">
                  <Button variant="ghost" size="sm" disabled>
                    <RiArrowLeftLine className="mr-1 h-4 w-4" />
                    Back
                  </Button>
                  <Button
                    onClick={submitAnswer}
                    disabled={!answer.trim() || loading}
                    className="gap-2"
                  >
                    {loading ? (
                      <RiLoader4Line className="h-4 w-4 animate-spin" />
                    ) : (
                      <RiArrowRightLine className="h-4 w-4" />
                    )}
                    {question.question_index + 1 >= question.total_questions
                      ? "Finish"
                      : "Next"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // ── Result Phase ─────────────────────────────────────────────
  if (phase === "result" && result) {
    const sections = [
      { key: "listening", label: "Listening", band: result.listening_band, icon: RiHeadphoneLine, color: "text-blue-600" },
      { key: "reading", label: "Reading", band: result.reading_band, icon: RiBookOpenLine, color: "text-emerald-600" },
      { key: "writing", label: "Writing", band: result.writing_band, icon: RiEdit2Line, color: "text-amber-600" },
      { key: "speaking", label: "Speaking", band: result.speaking_band, icon: RiMicLine, color: "text-purple-600" },
    ];

    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="w-full max-w-lg">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
              <span className="text-3xl font-bold text-primary">
                {result.overall_band}
              </span>
            </div>
            <h1 className="text-2xl font-semibold">Your Estimated Band</h1>
            <p className="mt-1 text-muted-foreground">
              Based on your diagnostic test performance
            </p>
          </div>

          {/* Section Scores */}
          <Card className="mb-6">
            <CardContent className="grid grid-cols-2 gap-4 pt-6">
              {sections.map((s) => (
                <div
                  key={s.key}
                  className="flex items-center gap-3 rounded-lg border border-border/50 p-3"
                >
                  <s.icon className={cn("h-5 w-5", s.color)} />
                  <div>
                    <div className="text-xs text-muted-foreground">
                      {s.label}
                    </div>
                    <div className="text-lg font-semibold">{s.band}</div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Strengths & Weaknesses */}
          <div className="mb-6 grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-emerald-600">
                  Strengths
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {result.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <RiCheckLine className="mt-0.5 h-3.5 w-3.5 text-emerald-500" />
                      {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-amber-600">
                  Focus Areas
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1 text-sm">
                  {result.focus_areas.map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <RiArrowRightLine className="mt-0.5 h-3.5 w-3.5 text-amber-500" />
                      {f}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          <Button className="w-full gap-2" size="lg" onClick={goToDashboard}>
            <RiArrowRightLine className="h-4 w-4" />
            Go to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  // Loading fallback
  return (
    <div className="flex min-h-screen items-center justify-center">
      <RiLoader4Line className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}
