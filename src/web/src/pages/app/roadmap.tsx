import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  RiBookOpenLine,
  RiCheckLine,
  RiEdit2Line,
  RiFlashlightLine,
  RiHeadphoneLine,
  RiLoader4Line,
  RiLockLine,
  RiMicLine,
  RiPlayLine,
  RiQuestionLine,
  RiRoadMapLine,
  RiStarLine,
  RiTrophyLine,
} from "@remixicon/react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { getUserFacingErrorMessage } from "@/lib/app-errors";
import { useOnboardingGate } from "./layout";
import { generateTopics, type TopicGeneratorResult } from "@/lib/ielts-api";
import { toast } from "sonner";
import {
  getPhaseTitle,
  getRoadmapStorageKey,
  loadRoadmapPhases,
  sectionMeta,
  type Phase,
  type PhaseQuiz,
} from "./roadmap-shared";

function generateQuizzes(topics: TopicGeneratorResult): PhaseQuiz[] {
  const quizzes: PhaseQuiz[] = [];

  for (const topic of topics.speaking_topics.slice(0, 1)) {
    quizzes.push({
      question: `In IELTS Speaking Part ${topic.part}, what is the best approach for the topic "${topic.topic}"?`,
      options: [
        "Give one-word answers to save time",
        `Use vocabulary like: ${topic.vocabulary_hints.slice(0, 3).join(", ")}`,
        "Speak as fast as possible without pausing",
        "Only answer exactly what is asked, nothing more",
      ],
      correctIndex: 1,
    });
  }

  for (const topic of topics.writing_topics.slice(0, 1)) {
    quizzes.push({
      question: `For a "${topic.task_type}" writing task, what should you focus on?`,
      options: [
        "Write as many words as possible",
        "Use only simple vocabulary to avoid mistakes",
        `Structure your response with a clear outline and use key vocabulary: ${topic.key_vocabulary.slice(0, 2).join(", ")}`,
        "Copy the prompt wording as much as possible",
      ],
      correctIndex: 2,
    });
  }

  for (const topic of topics.reading_topics.slice(0, 1)) {
    quizzes.push({
      question: `When answering "${topic.question_types[0] || "comprehension"}" questions about "${topic.passage_theme}", what strategy works best?`,
      options: [
        "Read every word carefully before looking at questions",
        "Scan for keywords and locate specific information",
        "Guess answers based on general knowledge",
        "Skip difficult passages entirely",
      ],
      correctIndex: 1,
    });
  }

  for (const topic of topics.listening_topics.slice(0, 1)) {
    quizzes.push({
      question: `In IELTS Listening Section ${topic.section} about "${topic.scenario}", what should you do?`,
      options: [
        "Write answers only after the recording ends",
        "Read the questions before the audio plays and predict answers",
        "Focus only on the first speaker",
        "Ignore any instructions given in the audio",
      ],
      correctIndex: 1,
    });
  }

  if (topics.weaknesses.length > 0) {
    quizzes.push({
      question: `Based on your profile, "${topics.weaknesses[0]}" is an area to improve. What's the best approach?`,
      options: [
        "Avoid practicing this area",
        "Focus all practice on strengths instead",
        "Practice consistently with targeted exercises and review feedback",
        "Wait until closer to the exam date",
      ],
      correctIndex: 2,
    });
  }

  return quizzes;
}

export default function RoadmapPage() {
  const { user } = useAuth();
  const { requireOnboarding } = useOnboardingGate();
  const roadmapStorageKey = getRoadmapStorageKey(user?.id);

  const [phases, setPhases] = useState<Phase[]>(() => loadRoadmapPhases(roadmapStorageKey));
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [quizPhaseId, setQuizPhaseId] = useState<number | null>(null);
  const [quizIndex, setQuizIndex] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState<number[]>([]);
  const [quizComplete, setQuizComplete] = useState(false);
  const [quizScore, setQuizScore] = useState(0);

  useEffect(() => {
    if (!roadmapStorageKey) return;
    if (phases.length > 0) {
      localStorage.setItem(roadmapStorageKey, JSON.stringify(phases));
      return;
    }
    localStorage.removeItem(roadmapStorageKey);
  }, [phases, roadmapStorageKey]);

  useEffect(() => {
    setPhases(loadRoadmapPhases(roadmapStorageKey));
  }, [roadmapStorageKey]);

  const activePhase = phases.find((phase) => phase.status === "active");
  const completedCount = phases.filter((phase) => phase.status === "completed").length;

  async function handleGenerate() {
    if (!user || requireOnboarding()) return;

    setGenerating(true);
    setError("");

    try {
      const result = await generateTopics(user.id, {
        target_score: user.target_band_score ?? 7.0,
        current_level_description: user.current_estimated_band
          ? `Currently at band ${user.current_estimated_band}`
          : undefined,
      });

      const nextPhaseNum = phases.length + 1;
      const newPhase: Phase = {
        id: nextPhaseNum,
        title: `Phase ${nextPhaseNum}: ${getPhaseTitle(nextPhaseNum, result)}`,
        description:
          result.assessment_summary ||
          result.study_plan_notes ||
          `Focus on: ${result.weaknesses.slice(0, 2).join(", ") || "all sections"}`,
        topics: result,
        status: phases.length === 0 ? "active" : "locked",
        quizzes: generateQuizzes(result),
        quizScore: null,
      };

      setPhases((current) => [...current, newPhase]);
      toast.success("Roadmap phase generated.");
    } catch (e) {
      const message = getUserFacingErrorMessage(
        e,
        "Couldn't generate your roadmap. Please try again."
      );
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  }

  function handleStartQuiz(phaseId: number) {
    setQuizPhaseId(phaseId);
    setQuizIndex(0);
    setQuizAnswers([]);
    setQuizComplete(false);
    setQuizScore(0);
  }

  function handleQuizAnswer(optionIndex: number) {
    const phase = phases.find((item) => item.id === quizPhaseId);
    if (!phase) return;

    const newAnswers = [...quizAnswers, optionIndex];
    setQuizAnswers(newAnswers);

    if (newAnswers.length >= phase.quizzes.length) {
      let correct = 0;
      phase.quizzes.forEach((question, index) => {
        if (newAnswers[index] === question.correctIndex) correct++;
      });

      const score = Math.round((correct / phase.quizzes.length) * 100);
      setQuizScore(score);
      setQuizComplete(true);

      if (score >= 60) {
        setPhases((current) =>
          current.map((item, itemIndex) => {
            if (item.id === quizPhaseId) return { ...item, status: "completed", quizScore: score };
            if (itemIndex > 0 && current[itemIndex - 1].id === quizPhaseId && item.status === "locked") {
              return { ...item, status: "active" };
            }
            return item;
          })
        );
        return;
      }

      setPhases((current) =>
        current.map((item) => (item.id === quizPhaseId ? { ...item, quizScore: score } : item))
      );
      return;
    }

    setQuizIndex(newAnswers.length);
  }

  function handleCloseQuiz() {
    setQuizPhaseId(null);
    setQuizComplete(false);
  }

  const currentQuiz =
    quizPhaseId != null
      ? phases.find((phase) => phase.id === quizPhaseId)?.quizzes[quizIndex]
      : null;
  const totalQuizQuestions =
    quizPhaseId != null
      ? phases.find((phase) => phase.id === quizPhaseId)?.quizzes.length ?? 0
      : 0;

  if (phases.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-12">
        <div className="text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10">
            <RiRoadMapLine className="h-10 w-10 text-primary" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Your Learning Roadmap</h1>
          <p className="mt-3 text-muted-foreground">
            AI will generate a personalized study roadmap for you, broken into phases.
            Complete each phase&apos;s content and pass the evaluation quiz to unlock the next phase.
          </p>

          {error && (
            <div className="mx-auto mt-4 max-w-sm rounded-md bg-destructive/10 px-4 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="mt-8 grid gap-3 text-left sm:grid-cols-2">
            {Object.entries(sectionMeta).map(([key, meta]) => (
              <div
                key={key}
                className="flex items-center gap-3 rounded-xl border border-border/50 p-3"
              >
                <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg", meta.bg)}>
                  <meta.icon className={cn("h-4 w-4", meta.color)} />
                </div>
                <div>
                  <div className="text-sm font-medium capitalize">{key}</div>
                  <div className="text-xs text-muted-foreground">Topics & practice</div>
                </div>
              </div>
            ))}
          </div>

          <Button size="lg" className="mt-8 gap-2" onClick={handleGenerate} disabled={generating}>
            {generating ? (
              <>
                <RiLoader4Line className="h-4 w-4 animate-spin" />
                Generating Phase 1...
              </>
            ) : (
              <>
                <RiFlashlightLine className="h-4 w-4" />
                Generate My Roadmap
              </>
            )}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Learning Roadmap</h1>
          <p className="text-sm text-muted-foreground">
            {completedCount} of {phases.length} phases completed
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleGenerate}
          disabled={generating || (activePhase != null && activePhase.status !== "completed")}
        >
          {generating ? (
            <RiLoader4Line className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RiFlashlightLine className="h-3.5 w-3.5" />
          )}
          {phases.length === 0 ? "Generate" : "Add Phase"}
        </Button>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="relative space-y-4">
        <div className="absolute bottom-0 left-5 top-0 w-px bg-border" />

        {phases.map((phase) => {
          const isLocked = phase.status === "locked";
          const isActive = phase.status === "active";
          const isCompleted = phase.status === "completed";

          return (
            <div key={phase.id} className="relative pl-12">
              <div
                className={cn(
                  "absolute left-3 top-4 flex h-5 w-5 items-center justify-center rounded-full border-2",
                  isCompleted && "border-emerald-500 bg-emerald-500 text-white",
                  isActive && "border-primary bg-primary text-primary-foreground",
                  isLocked && "border-border bg-muted text-muted-foreground"
                )}
              >
                {isCompleted ? (
                  <RiCheckLine className="h-3 w-3" />
                ) : isLocked ? (
                  <RiLockLine className="h-2.5 w-2.5" />
                ) : (
                  <span className="text-[10px] font-bold">{phase.id}</span>
                )}
              </div>

              <Card
                className={cn(
                  "transition-all",
                  isLocked && "opacity-50",
                  isActive && "border-primary/30 shadow-sm"
                )}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base">{phase.title}</CardTitle>
                        {isCompleted && (
                          <Badge className="bg-emerald-500/10 text-xs text-emerald-600">
                            Completed
                          </Badge>
                        )}
                        {isActive && (
                          <Badge className="bg-primary/10 text-xs text-primary">Active</Badge>
                        )}
                        {isLocked && (
                          <Badge variant="secondary" className="text-xs">
                            Locked
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{phase.description}</p>
                    </div>
                    {phase.quizScore != null && (
                      <div className="text-right">
                        <div className="text-xs text-muted-foreground">Quiz</div>
                        <div
                          className={cn(
                            "text-lg font-bold",
                            phase.quizScore >= 60 ? "text-emerald-600" : "text-amber-600"
                          )}
                        >
                          {phase.quizScore}%
                        </div>
                      </div>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {phase.topics.speaking_topics.length > 0 && (
                      <Badge variant="secondary" className="gap-1 text-xs">
                        <RiMicLine className="h-3 w-3" />
                        {phase.topics.speaking_topics.length} Speaking
                      </Badge>
                    )}
                    {phase.topics.writing_topics.length > 0 && (
                      <Badge variant="secondary" className="gap-1 text-xs">
                        <RiEdit2Line className="h-3 w-3" />
                        {phase.topics.writing_topics.length} Writing
                      </Badge>
                    )}
                    {phase.topics.reading_topics.length > 0 && (
                      <Badge variant="secondary" className="gap-1 text-xs">
                        <RiBookOpenLine className="h-3 w-3" />
                        {phase.topics.reading_topics.length} Reading
                      </Badge>
                    )}
                    {phase.topics.listening_topics.length > 0 && (
                      <Badge variant="secondary" className="gap-1 text-xs">
                        <RiHeadphoneLine className="h-3 w-3" />
                        {phase.topics.listening_topics.length} Listening
                      </Badge>
                    )}
                  </div>

                  {!isLocked && (
                    <div className="flex gap-2">
                      <Button asChild variant="outline" size="sm" className="gap-1.5">
                        <Link to={`/app/roadmap/${phase.id}`}>
                          <RiBookOpenLine className="h-3.5 w-3.5" />
                          View Content
                        </Link>
                      </Button>
                      {isActive && (
                        <Button
                          size="sm"
                          className="gap-1.5"
                          onClick={() => handleStartQuiz(phase.id)}
                        >
                          <RiQuestionLine className="h-3.5 w-3.5" />
                          Take Evaluation
                        </Button>
                      )}
                      {isCompleted && phase.quizScore != null && phase.quizScore < 100 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1.5 text-muted-foreground"
                          onClick={() => handleStartQuiz(phase.id)}
                        >
                          <RiPlayLine className="h-3.5 w-3.5" />
                          Retake Quiz
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          );
        })}

        {phases.every((phase) => phase.status === "completed") && (
          <div className="relative pl-12">
            <div className="absolute left-3 top-4 flex h-5 w-5 items-center justify-center rounded-full border-2 border-dashed border-primary/50">
              <RiStarLine className="h-2.5 w-2.5 text-primary" />
            </div>
            <Card className="border-dashed border-primary/30">
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="text-sm font-medium">Ready for the next phase?</p>
                  <p className="text-xs text-muted-foreground">
                    AI will generate new topics based on your progress
                  </p>
                </div>
                <Button
                  size="sm"
                  className="gap-1.5"
                  onClick={handleGenerate}
                  disabled={generating}
                >
                  {generating ? (
                    <RiLoader4Line className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <RiFlashlightLine className="h-3.5 w-3.5" />
                  )}
                  Generate
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      <Dialog open={quizPhaseId != null} onOpenChange={(open) => { if (!open) handleCloseQuiz(); }}>
        <DialogContent className="sm:max-w-lg">
          {!quizComplete && currentQuiz ? (
            <>
              <DialogHeader>
                <DialogTitle className="text-base">
                  Phase Evaluation - Question {quizIndex + 1} of {totalQuizQuestions}
                </DialogTitle>
                <DialogDescription className="sr-only">Answer the quiz question</DialogDescription>
              </DialogHeader>

              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${((quizIndex + 1) / totalQuizQuestions) * 100}%` }}
                />
              </div>

              <div className="py-2">
                <p className="mb-4 text-sm font-medium leading-relaxed">{currentQuiz.question}</p>
                <div className="space-y-2">
                  {currentQuiz.options.map((option, index) => (
                    <button
                      key={index}
                      onClick={() => handleQuizAnswer(index)}
                      className="w-full rounded-lg border border-border/50 p-3 text-left text-sm transition-all hover:border-primary hover:bg-primary/5"
                    >
                      <span className="mr-2 font-medium text-muted-foreground">
                        {String.fromCharCode(65 + index)}.
                      </span>
                      {option}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : quizComplete ? (
            <>
              <DialogHeader className="text-center sm:text-center">
                <div
                  className={cn(
                    "mx-auto mb-2 flex h-16 w-16 items-center justify-center rounded-full",
                    quizScore >= 60 ? "bg-emerald-500/10" : "bg-amber-500/10"
                  )}
                >
                  {quizScore >= 60 ? (
                    <RiTrophyLine className="h-8 w-8 text-emerald-600" />
                  ) : (
                    <RiQuestionLine className="h-8 w-8 text-amber-600" />
                  )}
                </div>
                <DialogTitle className="text-xl">
                  {quizScore >= 60 ? "Phase Complete!" : "Not quite yet"}
                </DialogTitle>
                <DialogDescription>
                  {quizScore >= 60
                    ? `You scored ${quizScore}% - the next phase is now unlocked!`
                    : `You scored ${quizScore}%. Review the phase content and try again (60% needed).`}
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button className="w-full" onClick={handleCloseQuiz}>
                  {quizScore >= 60 ? "Continue" : "Review & Retry"}
                </Button>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
