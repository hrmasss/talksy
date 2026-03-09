import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  RiArrowRightLine,
  RiBookOpenLine,
  RiEdit2Line,
  RiHeadphoneLine,
  RiMicLine,
  RiStarLine,
} from "@remixicon/react";
import type { TopicGeneratorResult } from "@/lib/ielts-api";

export const sectionMeta: Record<
  string,
  { icon: typeof RiMicLine; color: string; bg: string }
> = {
  listening: { icon: RiHeadphoneLine, color: "text-blue-600", bg: "bg-blue-500/10" },
  reading: { icon: RiBookOpenLine, color: "text-emerald-600", bg: "bg-emerald-500/10" },
  writing: { icon: RiEdit2Line, color: "text-amber-600", bg: "bg-amber-500/10" },
  speaking: { icon: RiMicLine, color: "text-purple-600", bg: "bg-purple-500/10" },
};

export interface PhaseQuiz {
  question: string;
  options: string[];
  correctIndex: number;
}

export interface Phase {
  id: number;
  title: string;
  description: string;
  topics: TopicGeneratorResult;
  status: "locked" | "active" | "completed";
  quizzes: PhaseQuiz[];
  quizScore: number | null;
}

export function getRoadmapStorageKey(userId?: string | null) {
  return userId ? `roadmap_${userId}` : null;
}

export function loadRoadmapPhases(storageKey: string | null): Phase[] {
  if (!storageKey) return [];

  const saved = localStorage.getItem(storageKey);
  if (!saved) return [];

  try {
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function RoadmapPhaseContent({ phase }: { phase: Phase }) {
  return (
    <div className="space-y-6">
      {phase.topics.speaking_topics.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-purple-500/10">
              <RiMicLine className="h-3.5 w-3.5 text-purple-600" />
            </div>
            Speaking Topics
          </h3>
          <div className="space-y-3">
            {phase.topics.speaking_topics.map((topic, index) => (
              <Card key={index}>
                <CardContent className="space-y-2 pt-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{topic.topic}</span>
                    <Badge variant="secondary" className="text-xs">
                      Part {topic.part}
                    </Badge>
                  </div>
                  {topic.cue_card && (
                    <p className="rounded-md bg-muted/50 p-2 text-xs italic text-muted-foreground">
                      {topic.cue_card}
                    </p>
                  )}
                  {topic.questions.length > 0 && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Questions:</span>
                      <ul className="mt-1 space-y-0.5">
                        {topic.questions.map((question, questionIndex) => (
                          <li
                            key={questionIndex}
                            className="flex gap-1.5 text-xs text-muted-foreground"
                          >
                            <RiArrowRightLine className="mt-0.5 h-3 w-3 shrink-0 text-purple-400" />
                            {question}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {topic.vocabulary_hints.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {topic.vocabulary_hints.map((hint, hintIndex) => (
                        <Badge key={hintIndex} variant="secondary" className="text-[10px]">
                          {hint}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {phase.topics.writing_topics.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-amber-500/10">
              <RiEdit2Line className="h-3.5 w-3.5 text-amber-600" />
            </div>
            Writing Tasks
          </h3>
          <div className="space-y-3">
            {phase.topics.writing_topics.map((topic, index) => (
              <Card key={index}>
                <CardContent className="space-y-2 pt-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{topic.task_type}</span>
                    <Badge variant="secondary" className="text-xs">
                      Task {topic.task}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{topic.prompt}</p>
                  {topic.sample_outline && (
                    <p className="rounded-md bg-muted/50 p-2 text-xs italic text-muted-foreground">
                      {topic.sample_outline}
                    </p>
                  )}
                  {topic.key_vocabulary.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {topic.key_vocabulary.map((vocabulary, vocabularyIndex) => (
                        <Badge key={vocabularyIndex} variant="secondary" className="text-[10px]">
                          {vocabulary}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {phase.topics.reading_topics.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-emerald-500/10">
              <RiBookOpenLine className="h-3.5 w-3.5 text-emerald-600" />
            </div>
            Reading Themes
          </h3>
          <div className="space-y-3">
            {phase.topics.reading_topics.map((topic, index) => (
              <Card key={index}>
                <CardContent className="space-y-2 pt-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{topic.passage_theme}</span>
                    <Badge variant="secondary" className="text-xs capitalize">
                      {topic.difficulty}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {topic.question_types.map((questionType, questionTypeIndex) => (
                      <Badge key={questionTypeIndex} variant="secondary" className="text-[10px]">
                        {questionType}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {phase.topics.listening_topics.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-blue-500/10">
              <RiHeadphoneLine className="h-3.5 w-3.5 text-blue-600" />
            </div>
            Listening Scenarios
          </h3>
          <div className="space-y-3">
            {phase.topics.listening_topics.map((topic, index) => (
              <Card key={index}>
                <CardContent className="space-y-2 pt-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{topic.scenario}</span>
                    <Badge variant="secondary" className="text-xs">
                      Section {topic.section}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {topic.question_types.map((questionType, questionTypeIndex) => (
                      <Badge key={questionTypeIndex} variant="secondary" className="text-[10px]">
                        {questionType}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {phase.topics.study_plan_notes && (
        <div className="rounded-lg border border-border/50 bg-muted/30 p-4">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <RiStarLine className="h-4 w-4 text-primary" />
            Study Notes
          </h3>
          <p className="text-sm text-muted-foreground">{phase.topics.study_plan_notes}</p>
        </div>
      )}
    </div>
  );
}

export function getPhaseTitle(num: number, result: TopicGeneratorResult): string {
  const titles: Record<number, string> = {
    1: "Foundation",
    2: "Building Skills",
    3: "Advanced Practice",
    4: "Exam Simulation",
    5: "Final Polish",
  };

  if (titles[num]) return titles[num];
  if (result.weaknesses.length > 0) return result.weaknesses[0];
  return `Advanced ${num}`;
}
