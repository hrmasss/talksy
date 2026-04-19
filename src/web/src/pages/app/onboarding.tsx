import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  RiArrowRightLine,
  RiCheckLine,
  RiLoader4Line,
  RiHeadphoneLine,
  RiBookOpenLine,
  RiEdit2Line,
  RiMicLine,
  RiStarLine,
  RiVolumeUpLine,
  RiStopCircleLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { getAssetUrl } from "@/lib/api-client";
import {
  getActivePlacementTest,
  startPlacementTest,
  submitPlacementAnswer,
  type PlacementQuestion,
  type PlacementResult,
} from "@/lib/ielts-api";
import { useAuth } from "@/lib/auth";
import { getCurrentUser } from "@/lib/auth-api";
import { getUserFacingErrorMessage } from "@/lib/app-errors";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { toast } from "sonner";

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
  const { user, setUser } = useAuth();

  // Setup phase
  const [targetBand, setTargetBand] = useState(7.0);
  const [examDate, setExamDate] = useState("");

  // Test phase
  const [phase, setPhase] = useState<Phase>("setup");
  const [question, setQuestion] = useState<PlacementQuestion | null>(null);

  const parsedQuestionData = question?.question_text ? (() => {
    try {
      if (question.question_text.trim().startsWith("{")) {
        return JSON.parse(question.question_text);
      }
    } catch {
      return null;
    }
    return null;
  })() : null;

  const displayQuestionText = parsedQuestionData?.question || parsedQuestionData?.question_text || (question?.question_text ?? "");
  const displayOptions = (parsedQuestionData?.options && Array.isArray(parsedQuestionData.options)) ? parsedQuestionData.options : (question?.options || []);
  const displayPassage = parsedQuestionData?.passage || (question as any)?.passage || null;
  const isListeningQuestion = question?.section === "listening";

  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<PlacementResult | null>(null);

  const { isRecording, startRecording, stopRecording } = useAudioRecorder();

  // Handle auto-playing audio for listening questions
  useEffect(() => {
    if (phase === "test" && question?.audio_url) {
      const audio = new Audio(getAssetUrl(question.audio_url));
      audio.play().catch((err) => {
        console.warn("Auto-play blocked or failed:", err);
      });
    }
  }, [phase, question?.audio_url, question?.question_index]);

  useEffect(() => {
    if (!user || user.onboarding_completed) {
      if (!user?.onboarding_completed) setLoading(false);
      return;
    }

    let cancelled = false;
    const resume = async () => {
      try {
        const active = await getActivePlacementTest(user.id);
        if (cancelled) return;

        if (!active) {
          setLoading(false);
          return;
        }

        if (active.status === "completed") {
          setResult(active as PlacementResult);
          const latestUser = await getCurrentUser();
          if (!cancelled) {
            setUser(latestUser);
            setPhase("result");
            toast.success("Placement test already completed.");
          }
          return;
        }

        setQuestion(active as PlacementQuestion);
        setPhase("test");
        toast.success("Resumed your placement test.");
      } catch (err) {
        console.error("Failed to resume placement test:", err);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void resume();
    return () => {
      cancelled = true;
    };
  }, [user, setUser]);

  const startTest = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const q = await startPlacementTest(user.id, {
        target_band_score: targetBand,
        exam_date: examDate || undefined,
      });
      if (q.status === "completed") {
        setResult(q as PlacementResult);
        const latestUser = await getCurrentUser();
        setUser(latestUser);
        setPhase("result");
        toast.success("Placement test completed successfully.");
      } else {
        setQuestion(q as PlacementQuestion);
        setPhase("test");
        toast.success("Placement test started.");
      }
    } catch (err) {
      console.error("Failed to start placement test:", err);
      toast.error(
        getUserFacingErrorMessage(
          err,
          "Couldn't start the placement test. Please try again."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!question || (question.question_type !== 'speaking' && !answer.trim() && !isRecording)) return;
    setLoading(true);
    try {
      let audioBase64: string | undefined;
      const finalAnswer = answer.trim() || undefined;
      
      if (isRecording) {
        toast.info("Processing your speech...");
        const blob = await stopRecording();
        audioBase64 = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = (reader.result as string).split(',')[1];
            resolve(base64);
          };
          reader.readAsDataURL(blob);
        });
      }

      const res = await submitPlacementAnswer(
        question.thread_id, 
        finalAnswer,
        audioBase64
      );
      setAnswer("");

      if (res.status === "completed") {
        setResult(res as PlacementResult);
        const latestUser = await getCurrentUser();
        setUser(latestUser);
        setPhase("result");
        toast.success("Placement test completed successfully.");
      } else {
        setQuestion(res as PlacementQuestion);
        toast.success("Answer submitted.");
      }
    } catch (err) {
      console.error("Failed to submit answer:", err);
      toast.error(
        getUserFacingErrorMessage(
          err,
          "Couldn't submit your answer. Please try again."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const goToDashboard = () => {
    navigate("/app");
  };

  // ── Setup Phase ──────────────────────────────────────────────
  if (phase === "setup") {
    if (loading) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background p-6">
          <RiLoader4Line className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

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
            {!isListeningQuestion && displayPassage && (
              <Card className="mb-4">
                <CardContent className="prose prose-sm dark:prose-invert max-h-60 overflow-y-auto pt-4 text-sm">
                  <div className="whitespace-pre-wrap">{displayPassage}</div>
                </CardContent>
              </Card>
            )}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-lg leading-relaxed">
                  <div className="flex-1 whitespace-pre-wrap">
                    {isListeningQuestion
                      ? "Listen to the audio carefully, then write your answer below."
                      : displayQuestionText}
                  </div>
                  {question.audio_url && (
                    <Button
                      variant="outline"
                      size="icon"
                      className="ml-4 h-10 w-10 shrink-0 rounded-full"
                      onClick={() => {
                        const audio = new Audio(getAssetUrl(question.audio_url!));
                        audio.play();
                      }}
                    >
                      <RiVolumeUpLine className="h-5 w-5" />
                    </Button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Speaking Section: Mic Control */}
                {question.section === "speaking" && (
                  <div className="flex flex-col items-center justify-center space-y-4 rounded-lg bg-muted/50 py-8">
                    <div className="mb-2 text-center text-sm font-medium text-muted-foreground">
                      {isRecording ? "Recording..." : "Click to start recording"}
                    </div>
                    <Button
                      size="lg"
                      variant={isRecording ? "destructive" : "default"}
                      className={cn(
                        "h-16 w-16 rounded-full",
                        isRecording && "animate-pulse"
                      )}
                      onClick={() => (isRecording ? stopRecording() : startRecording())}
                    >
                      {isRecording ? (
                        <RiStopCircleLine className="h-8 w-8" />
                      ) : (
                        <RiMicLine className="h-8 w-8" />
                      )}
                    </Button>
                    <p className="px-4 text-center text-xs text-muted-foreground">
                      {isRecording 
                        ? "Speak clearly into your microphone" 
                        : "Your speech will be automatically transcribed"}
                    </p>
                  </div>
                )}

                {/* Options for MCQ */}
                {displayOptions && displayOptions.length > 0 ? (
                  <div className="space-y-2">
                    {displayOptions.map((opt: string, i: number) => (
                      <Button
                        key={i}
                        variant={answer === opt ? "default" : "outline"}
                        className="w-full justify-start text-left"
                        onClick={() => setAnswer(opt)}
                      >
                        <span className="mr-2 font-medium text-muted-foreground">
                          {String.fromCharCode(65 + i)}.
                        </span>
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
                        : question.section === "speaking"
                          ? "Optional: Edit your transcription here..."
                          : "Type your answer..."
                    }
                    className="min-h-[120px]"
                  />
                )}

                <div className="flex justify-between">
                  {/* Status Indicator */}
                  {question.section === "speaking" && isRecording && (
                    <div className="flex items-center gap-2 text-xs font-medium text-destructive animate-pulse">
                      <div className="h-2 w-2 rounded-full bg-destructive" />
                      Live Recording
                    </div>
                  )}
                  <div className="flex-1" />
                  <Button
                    onClick={submitAnswer}
                    disabled={(!answer.trim() && !isRecording && question.section !== 'speaking') || loading}
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
