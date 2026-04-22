import { useState, useEffect, useRef, useCallback } from "react";
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
  RiHistoryLine,
  RiLoader4Line,
  RiMicLine,
  RiPlayLine,
  RiStopCircleLine,
  RiTimeLine,
  RiVolumeUpLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { getAssetUrl } from "@/lib/api-client";
import {
  startMockTest,
  submitMockAnswer,
  getActiveMockTest,
  listMockTestSessions,
  resumeMockTest,
  type MockTestQuestion,
  type MockTestReport,
  type MockExamSession,
} from "@/lib/ielts-api";
import { useAuth } from "@/lib/auth";
import { getUserFacingErrorMessage } from "@/lib/app-errors";
import { toast } from "sonner";
import { useOnboardingGate } from "./onboarding-gate";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { speechToText } from "@/lib/speech-api";
import { playStreamingTextToSpeech, type StreamingAudioPlayback } from "@/lib/tts-stream-player";
import {
  attachPhaseEvaluationReport,
  getRoadmapStorageKey,
  loadRoadmapPhases,
  saveRoadmapPhases,
} from "./roadmap-shared";

type Phase = "setup" | "test" | "report" | "history";

const sections = [
  { key: "listening", label: "Listening", icon: RiHeadphoneLine, color: "text-blue-600", bg: "bg-blue-500/10" },
  { key: "reading", label: "Reading", icon: RiBookOpenLine, color: "text-emerald-600", bg: "bg-emerald-500/10" },
  { key: "writing", label: "Writing", icon: RiEdit2Line, color: "text-amber-600", bg: "bg-amber-500/10" },
  { key: "speaking", label: "Speaking", icon: RiMicLine, color: "text-purple-600", bg: "bg-purple-500/10" },
  { key: "full", label: "Full Test", icon: RiFlashlightLine, color: "text-primary", bg: "bg-primary/10" },
] as const;

/** Sections where question audio should auto-play */
const AUDIO_SECTIONS = new Set(["listening", "speaking"]);

export default function MockTestPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const roadmapEvaluation = searchParams.get("roadmapEvaluation") === "1";
  const roadmapPhaseId = Number(searchParams.get("roadmapPhaseId"));
  const initialSection = roadmapEvaluation ? "full" : searchParams.get("section") || "";
  const { requireOnboarding } = useOnboardingGate();

  const [phase, setPhase] = useState<Phase>("setup");
  const [selectedSection, setSelectedSection] = useState(initialSection);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<MockTestQuestion | null>(null);

  const parsedQuestionData = question?.question_text ? (() => {
    try {
      const trimmed = question.question_text.trim();
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        return JSON.parse(trimmed);
      }
    } catch {
      return null;
    }
    return null;
  })() : null;

  const displayPassage = parsedQuestionData?.passage || question?.passage;
  const displayQuestionText = parsedQuestionData?.question || parsedQuestionData?.question_text || (typeof parsedQuestionData === "string" ? parsedQuestionData : question?.question_text);
  const displayOptions = (parsedQuestionData?.options && Array.isArray(parsedQuestionData.options)) ? parsedQuestionData.options : question?.options;
  const isListeningQuestion = question?.section === "listening";

  const [report, setReport] = useState<MockTestReport | null>(null);
  const [answer, setAnswer] = useState("");
  const [transcribing, setTranscribing] = useState(false);
  const [ttsPlaying, setTtsPlaying] = useState(false);

  // Session management
  const [activeSession, setActiveSession] = useState<MockExamSession | null>(null);
  const [sessions, setSessions] = useState<MockExamSession[]>([]);
  const [checkingSession, setCheckingSession] = useState(true);

  // Audio cache for replay
  const questionAudioRef = useRef<HTMLAudioElement | null>(null);
  const questionAudioUrlRef = useRef<string | null>(null);
  const streamingAudioRef = useRef<StreamingAudioPlayback | null>(null);

  const { isRecording, startRecording, stopRecording } = useAudioRecorder();

  useEffect(() => {
    if (!roadmapEvaluation) return;
    setSelectedSection("full");
  }, [roadmapEvaluation]);

  useEffect(() => {
    if (!user || !roadmapEvaluation || !report || !Number.isFinite(roadmapPhaseId)) return;

    const storageKey = getRoadmapStorageKey(user.id);
    const phases = loadRoadmapPhases(storageKey);
    const updated = attachPhaseEvaluationReport(phases, roadmapPhaseId, report);
    saveRoadmapPhases(storageKey, updated);
  }, [report, roadmapEvaluation, roadmapPhaseId, user]);

  // ── Check for active / past sessions on mount ────────────
  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    (async () => {
      try {
        const [active, history] = await Promise.all([
          getActiveMockTest(user.id).catch(() => null),
          listMockTestSessions(user.id, { limit: 10 }).catch(() => ({ items: [] })),
        ]);
        if (cancelled) return;
        setActiveSession(active ?? null);
        setSessions(history.items);
      } finally {
        if (!cancelled) setCheckingSession(false);
      }
    })();

    return () => { cancelled = true; };
  }, [user]);

  // ── Generate / fetch audio for question (listening & speaking) ──
  const playQuestionAudio = useCallback(
    async (q: MockTestQuestion) => {
      if (!AUDIO_SECTIONS.has(q.section) || !q.question_text) return;

      setTtsPlaying(true);
      try {
        if (questionAudioRef.current) {
          questionAudioRef.current.pause();
          questionAudioRef.current = null;
        }
        if (questionAudioUrlRef.current?.startsWith("blob:")) {
          URL.revokeObjectURL(questionAudioUrlRef.current);
        }
        questionAudioUrlRef.current = null;
        if (streamingAudioRef.current) {
          streamingAudioRef.current.stop();
          streamingAudioRef.current = null;
        }

        // Prefer server-cached audio if URL provided.
        if (q.audio_url) {
          const resolvedAudioUrl = getAssetUrl(q.audio_url);
          questionAudioUrlRef.current = resolvedAudioUrl;
          const audio = new Audio(resolvedAudioUrl);
          questionAudioRef.current = audio;
          audio.onended = () => setTtsPlaying(false);
          audio.onerror = () => setTtsPlaying(false);
          await audio.play();
          return;
        }

        const playback = await playStreamingTextToSpeech(q.question_text);
        streamingAudioRef.current = playback;
        questionAudioRef.current = null;
        questionAudioUrlRef.current = null;
        void playback.finished.finally(() => {
          if (streamingAudioRef.current === playback) {
            streamingAudioRef.current = null;
            setTtsPlaying(false);
          }
        });
      } catch {
        toast.error("Could not play audio. Check API key in Settings.");
        setTtsPlaying(false);
      }
    },
    []
  );

  // Auto-play audio whenever question changes (listening/speaking)
  useEffect(() => {
    if (phase === "test" && question && AUDIO_SECTIONS.has(question.section)) {
      playQuestionAudio(question);
    }
    // Cleanup on unmount
    return () => {
      if (questionAudioRef.current) {
        questionAudioRef.current.pause();
        questionAudioRef.current = null;
      }
      if (streamingAudioRef.current) {
        streamingAudioRef.current.stop();
        streamingAudioRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question?.question_index, phase]);

  const handleReplayAudio = () => {
    if (questionAudioRef.current) {
      setTtsPlaying(true);
      questionAudioRef.current.currentTime = 0;
      questionAudioRef.current.play();
    } else if (question) {
      playQuestionAudio(question);
    }
  };

  // ── STT: record voice answer ─────────────────────────────────
  const handleToggleRecording = async () => {
    if (isRecording) {
      setTranscribing(true);
      try {
        const blob = await stopRecording();
        if (blob.size > 0) {
          const text = await speechToText(blob);
          setAnswer((prev) => (prev ? prev + " " + text : text));
        }
      } catch {
        toast.error("Could not transcribe audio. Check API key in Settings.");
      } finally {
        setTranscribing(false);
      }
    } else {
      try {
        await startRecording();
      } catch {
        toast.error("Microphone access denied.");
      }
    }
  };

  // ── Start a new exam ───────────────────────────────────
  async function handleStart() {
    if (!user || requireOnboarding()) return;
    setLoading(true);
    try {
      const q = await startMockTest(user.id, {
        test_type: selectedSection === "full" ? "full" : "section",
        section: selectedSection === "full" ? undefined : selectedSection,
      });
      setQuestion(q);
      setPhase("test");
      setAnswer("");
      setActiveSession(null);
      toast.success("Mock test started.");
    } catch (e) {
      console.error(e);
      toast.error(
        getUserFacingErrorMessage(
          e,
          "Couldn't start the mock test. Please try again."
        )
      );
    } finally {
      setLoading(false);
    }
  }

  // ── Resume an in-progress exam ─────────────────────────
  async function handleResume(threadId: string) {
    setLoading(true);
    try {
      const result = await resumeMockTest(threadId);
      if (result.status === "completed") {
        setReport(result as MockTestReport);
        setPhase("report");
      } else {
        setQuestion(result as MockTestQuestion);
        setPhase("test");
        setAnswer("");
      }
      setActiveSession(null);
      toast.success("Resumed your mock test.");
    } catch (e) {
      console.error(e);
      toast.error(
        getUserFacingErrorMessage(e, "Couldn't resume the test. It may have expired.")
      );
    } finally {
      setLoading(false);
    }
  }

  // ── Submit answer ──────────────────────────────────────
  async function handleSubmit() {
    if (!question || !answer.trim()) return;
    setLoading(true);
    try {
      const result = await submitMockAnswer(question.thread_id, answer.trim());
      if (result.status === "completed") {
        setReport(result as MockTestReport);
        setPhase("report");
        toast.success("Mock test completed.");
      } else {
        setQuestion(result as MockTestQuestion);
        setAnswer("");
        toast.success("Answer submitted.");
      }
    } catch (e) {
      console.error(e);
      toast.error(
        getUserFacingErrorMessage(
          e,
          "Couldn't submit your answer. Please try again."
        )
      );
    } finally {
      setLoading(false);
    }
  }

  // ── Loading state on first mount ──────────────────────
  if (checkingSession) {
    return (
      <div className="flex items-center justify-center py-20">
        <RiLoader4Line className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ── History Phase ─────────────────────────────────────────────
  if (phase === "history") {
    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">Exam History</h1>
          <Button variant="outline" size="sm" onClick={() => setPhase("setup")}>
            <RiArrowLeftLine className="mr-1.5 h-4 w-4" /> Back
          </Button>
        </div>

        {sessions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No exam history yet.</p>
        ) : (
          <div className="space-y-3">
            {sessions.map((s) => (
              <Card
                key={s.thread_id}
                className={cn(
                  "cursor-pointer transition-all hover:border-primary/40",
                  s.status === "in_progress" && "border-amber-400/60"
                )}
                onClick={() => {
                  if (s.status === "in_progress") {
                    handleResume(s.thread_id);
                  } else if (s.status === "completed" && s.band_score != null) {
                    // Show report for completed sessions
                    setReport({
                      thread_id: s.thread_id,
                      status: "completed",
                      section: s.section,
                      overall_band: s.band_score,
                      section_scores: s.section_scores,
                      evaluations: [],
                      strengths: s.strengths,
                      weaknesses: s.weaknesses,
                      recommendations: s.recommendations,
                      final_report_markdown: s.report_markdown,
                    });
                    setPhase("report");
                  }
                }}
              >
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={s.status === "in_progress" ? "default" : "secondary"}
                      className="capitalize"
                    >
                      {s.section}
                    </Badge>
                    <div>
                      <div className="text-sm font-medium capitalize">{s.status.replace("_", " ")}</div>
                      <div className="text-xs text-muted-foreground">
                        {s.started_at
                          ? new Date(s.started_at).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : ""}
                        {" · "}Q{s.question_index}/{s.total_questions}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {s.band_score != null ? (
                      <span className="text-lg font-bold text-primary">{s.band_score}</span>
                    ) : s.status === "in_progress" ? (
                      <Badge variant="outline" className="text-amber-600">Resume</Badge>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Setup Phase ───────────────────────────────────────────────
  if (phase === "setup") {
    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        <div className="mb-2 flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">Mock Test</h1>
          {sessions.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-muted-foreground"
              onClick={() => setPhase("history")}
            >
              <RiHistoryLine className="h-4 w-4" />
              History
            </Button>
          )}
        </div>
        <p className="mb-6 text-sm text-muted-foreground">
          {roadmapEvaluation
            ? "This full mock test will be saved as the evaluation for your current roadmap phase."
            : "Choose a section to practice or take a full test."}
        </p>

        {/* Resume Banner */}
        {activeSession && (
          <Card className="mb-4 border-amber-400/60 bg-amber-500/5">
            <CardContent className="flex items-center justify-between py-4">
              <div>
                <div className="text-sm font-medium">
                  You have an in-progress <span className="capitalize">{activeSession.section}</span> test
                </div>
                <div className="text-xs text-muted-foreground">
                  Q{activeSession.question_index}/{activeSession.total_questions}
                  {activeSession.started_at &&
                    ` · Started ${new Date(activeSession.started_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`}
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => handleResume(activeSession.thread_id)}
                disabled={loading}
              >
                {loading ? (
                  <RiLoader4Line className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RiPlayLine className="mr-1.5 h-3.5 w-3.5" />
                )}
                Resume
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {sections.map((s) => (
            <button
              key={s.key}
              onClick={() => {
                if (!roadmapEvaluation) {
                  setSelectedSection(s.key);
                }
              }}
              className={cn(
                "flex items-center gap-3 rounded-xl border p-4 text-left transition-all",
                selectedSection === s.key
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "border-border/50 hover:border-border",
                roadmapEvaluation && s.key !== "full" && "cursor-not-allowed opacity-50"
              )}
              disabled={roadmapEvaluation && s.key !== "full"}
            >
              <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg", s.bg)}>
                <s.icon className={cn("h-5 w-5", s.color)} />
              </div>
              <div>
                <div className="font-medium">{s.label}</div>
                <div className="text-xs text-muted-foreground">
                  {roadmapEvaluation && s.key === "full"
                    ? "Required roadmap evaluation"
                    : s.key === "full"
                      ? "All 4 sections"
                      : `${s.label} section only`}
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
          {roadmapEvaluation ? "Start Phase Evaluation" : "Start Test"}
        </Button>
      </div>
    );
  }

  // ── Test Phase ────────────────────────────────────────────────
  if (phase === "test" && question) {
    const pct = ((question.question_index + 1) / question.total_questions) * 100;
    const isAudioSection = AUDIO_SECTIONS.has(question.section);

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
        {!isListeningQuestion && displayPassage && (
          <Card className="mb-4">
            <CardContent className="prose prose-sm dark:prose-invert max-h-60 overflow-y-auto pt-4 text-sm">
              {displayPassage.includes("<") ? (
                <div dangerouslySetInnerHTML={{ __html: displayPassage }} />
              ) : (
                <div className="whitespace-pre-wrap">{displayPassage}</div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Question */}
        <Card className="mb-4">
          <CardContent className="pt-6">
            <div className="mb-4 text-sm font-medium leading-relaxed whitespace-pre-wrap">
              {isListeningQuestion
                ? "Listen to the audio carefully, then write your answer."
                : displayQuestionText}
            </div>

            {/* Replay / Listen button for audio sections */}
            {isAudioSection && (
              <div className="mb-3">
                <Button
                  variant="outline"
                  size="sm"
                  className={cn(
                    "gap-1.5",
                    ttsPlaying && "border-primary/40 bg-primary/5 text-primary"
                  )}
                  onClick={handleReplayAudio}
                  disabled={ttsPlaying}
                >
                  <RiVolumeUpLine
                    className={cn("h-3.5 w-3.5", ttsPlaying && "animate-pulse")}
                  />
                  {ttsPlaying ? "Playing audio" : "Replay Question"}
                </Button>
              </div>
            )}

            {displayOptions && displayOptions.length > 0 ? (
              <div className="space-y-2">
                {displayOptions.map((opt: string, i: number) => (
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
              <div className="space-y-2">
                <Textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder={
                    question.section === "speaking"
                      ? "Click the mic to record your answer, or type it…"
                      : "Type your answer here…"
                  }
                  className="min-h-30 resize-none"
                />
                {question.section === "speaking" && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant={isRecording ? "destructive" : "outline"}
                      size="sm"
                      className={cn("gap-1.5", isRecording && "animate-pulse")}
                      onClick={handleToggleRecording}
                      disabled={transcribing}
                    >
                      {transcribing ? (
                        <RiLoader4Line className="h-3.5 w-3.5 animate-spin" />
                      ) : isRecording ? (
                        <RiStopCircleLine className="h-3.5 w-3.5" />
                      ) : (
                        <RiMicLine className="h-3.5 w-3.5" />
                      )}
                      {transcribing ? "Transcribing…" : isRecording ? "Stop" : "Record"}
                    </Button>
                  </div>
                )}
              </div>
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
                    <span className="max-w-45 truncate text-xs text-muted-foreground">
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
              // Refresh session list
              if (user) {
                listMockTestSessions(user.id, { limit: 10 })
                  .then((r) => setSessions(r.items))
                  .catch(() => {});
              }
            }}
          >
            <RiArrowLeftLine className="mr-2 h-4 w-4" />
            {roadmapEvaluation ? "Retake Evaluation" : "Take Another Test"}
          </Button>
          <Link
            to={roadmapEvaluation && Number.isFinite(roadmapPhaseId) ? `/app/roadmap/${roadmapPhaseId}` : "/app/dashboard"}
            className="flex-1"
          >
            <Button className="w-full">
              {roadmapEvaluation ? "Back to Roadmap" : "Go to Dashboard"}
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return null;
}
