import type { ReactNode } from "react";
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
import type {
  MockTestReport,
  SectionScore,
  TopicGeneratorResult,
  TopicListeningTopic,
  TopicReadingTopic,
  TopicSpeakingTopic,
  TopicWritingTopic,
} from "@/lib/ielts-api";

export const sectionMeta: Record<
  string,
  { icon: typeof RiMicLine; color: string; bg: string; border: string }
> = {
  listening: {
    icon: RiHeadphoneLine,
    color: "text-blue-700",
    bg: "bg-blue-100",
    border: "border-blue-200",
  },
  reading: {
    icon: RiBookOpenLine,
    color: "text-emerald-700",
    bg: "bg-emerald-100",
    border: "border-emerald-200",
  },
  writing: {
    icon: RiEdit2Line,
    color: "text-amber-700",
    bg: "bg-amber-100",
    border: "border-amber-200",
  },
  speaking: {
    icon: RiMicLine,
    color: "text-violet-700",
    bg: "bg-violet-100",
    border: "border-violet-200",
  },
};

export interface Phase {
  id: number;
  title: string;
  description: string;
  topics: TopicGeneratorResult;
  status: "active" | "saved";
  completed_topic_ids: string[];
  evaluation_report: RoadmapEvaluationReport | null;
}

export interface RoadmapTopicEntry {
  id: string;
  section: "speaking" | "writing" | "reading" | "listening";
  title: string;
  detail: string;
}

export interface RoadmapEvaluationReport {
  thread_id: string;
  status: "completed";
  section?: string | null;
  overall_band?: number | null;
  section_scores: SectionScore[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  final_report_markdown?: string | null;
  completed_at: string;
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
    if (!Array.isArray(parsed)) return [];

    return parsed.map((item, index, all) => ({
      id: Number(item?.id) || index + 1,
      title: typeof item?.title === "string" ? item.title : `Roadmap ${index + 1}`,
      description: typeof item?.description === "string" ? item.description : "",
      topics: item?.topics ?? {
        section_estimates: {},
        strengths: [],
        weaknesses: [],
        speaking_topics: [],
        writing_topics: [],
        reading_topics: [],
        listening_topics: [],
      },
      status: index === all.length - 1 ? "active" : "saved",
      completed_topic_ids: Array.isArray(item?.completed_topic_ids)
        ? item.completed_topic_ids.filter((value: unknown): value is string => typeof value === "string")
        : [],
      evaluation_report:
        item?.evaluation_report && typeof item.evaluation_report === "object"
          ? item.evaluation_report
          : null,
    }));
  } catch {
    return [];
  }
}

export function saveRoadmapPhases(storageKey: string | null, phases: Phase[]) {
  if (!storageKey) return;

  if (phases.length === 0) {
    localStorage.removeItem(storageKey);
    return;
  }

  localStorage.setItem(storageKey, JSON.stringify(phases));
}

export function getPhaseTopicEntries(phase: Phase): RoadmapTopicEntry[] {
  return [
    ...phase.topics.speaking_topics.map((topic, index) => ({
      id: `speaking-${index}`,
      section: "speaking" as const,
      title: topic.topic,
      detail: `Speaking Part ${topic.part}`,
    })),
    ...phase.topics.writing_topics.map((topic, index) => ({
      id: `writing-${index}`,
      section: "writing" as const,
      title: topic.task_type,
      detail: `Writing Task ${topic.task}`,
    })),
    ...phase.topics.reading_topics.map((topic, index) => ({
      id: `reading-${index}`,
      section: "reading" as const,
      title: topic.passage_theme,
      detail: `Reading ${topic.difficulty}`,
    })),
    ...phase.topics.listening_topics.map((topic, index) => ({
      id: `listening-${index}`,
      section: "listening" as const,
      title: topic.scenario,
      detail: `Listening Section ${topic.section}`,
    })),
  ];
}

export function getPhaseCompletedCount(phase: Phase) {
  const validIds = new Set(getPhaseTopicEntries(phase).map((item) => item.id));
  return phase.completed_topic_ids.filter((id) => validIds.has(id)).length;
}

export function isPhasePracticeComplete(phase: Phase) {
  const total = getPhaseTopicEntries(phase).length;
  return total > 0 && getPhaseCompletedCount(phase) >= total;
}

export function isPhaseEvaluationComplete(phase: Phase) {
  return Boolean(phase.evaluation_report);
}

export function getPhaseEvaluationState(phase: Phase) {
  if (isPhaseEvaluationComplete(phase)) return "completed";
  if (isPhasePracticeComplete(phase)) return "ready";
  return "locked";
}

export function togglePhaseTopicCompletion(
  phases: Phase[],
  phaseId: number,
  topicId: string
): Phase[] {
  return phases.map((phase) => {
    if (phase.id !== phaseId) return phase;

    const nextIds = phase.completed_topic_ids.includes(topicId)
      ? phase.completed_topic_ids.filter((id) => id !== topicId)
      : [...phase.completed_topic_ids, topicId];

    return {
      ...phase,
      completed_topic_ids: nextIds,
      evaluation_report: nextIds.length === getPhaseTopicEntries(phase).length
        ? phase.evaluation_report
        : null,
    };
  });
}

export function attachPhaseEvaluationReport(
  phases: Phase[],
  phaseId: number,
  report: MockTestReport
): Phase[] {
  return phases.map((phase) => {
    if (phase.id !== phaseId) return phase;

    return {
      ...phase,
      completed_topic_ids: getPhaseTopicEntries(phase).map((item) => item.id),
      evaluation_report: {
        thread_id: report.thread_id,
        status: "completed",
        section: report.section,
        overall_band: report.overall_band,
        section_scores: report.section_scores,
        strengths: report.strengths,
        weaknesses: report.weaknesses,
        recommendations: report.recommendations,
        final_report_markdown: report.final_report_markdown,
        completed_at: new Date().toISOString(),
      },
    };
  });
}

function SectionHeader({
  title,
  count,
  icon: Icon,
  bg,
  color,
}: {
  title: string;
  count: number;
  icon: typeof RiMicLine;
  bg: string;
  color: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-3">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center border ${bg}`}>
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
        <div>
          <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
          <p className="text-sm text-muted-foreground">4 guided practice items for this skill</p>
        </div>
      </div>
      <Badge variant="outline" className="px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em]">
        {count} Items
      </Badge>
    </div>
  );
}

function Checklist({ items }: { items: string[] }) {
  if (items.length === 0) return null;

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

function ChipRow({ items }: { items: string[] }) {
  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <Badge key={`${item}-${index}`} variant="secondary" className="px-3 py-1 text-xs font-medium">
          {item}
        </Badge>
      ))}
    </div>
  );
}

function TopicPanel({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
}) {
  return (
    <Card className="border border-border bg-card/95 shadow-none">
      <CardContent className="space-y-5 p-6">
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {eyebrow}
          </div>
          <h4 className="text-xl font-semibold leading-tight">{title}</h4>
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

function SpeakingTopicCard({ topic }: { topic: TopicSpeakingTopic }) {
  return (
    <TopicPanel title={topic.topic} eyebrow={`Speaking Part ${topic.part}`}>
      {topic.practice_focus && (
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Practice Focus
          </p>
          <p className="text-[15px] leading-7 text-foreground/90">{topic.practice_focus}</p>
        </div>
      )}

      {topic.cue_card && (
        <div className="border border-border bg-muted/30 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Cue Card
          </p>
          <p className="mt-2 whitespace-pre-wrap text-[15px] leading-7 text-foreground/90">
            {topic.cue_card}
          </p>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Questions
          </p>
          <Checklist items={topic.questions} />
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Answer Framework
          </p>
          <Checklist items={topic.answer_framework} />
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Helpful Vocabulary
        </p>
        <ChipRow items={topic.vocabulary_hints} />
      </div>

      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Common Mistakes To Avoid
        </p>
        <Checklist items={topic.common_mistakes} />
      </div>
    </TopicPanel>
  );
}

function WritingTopicCard({ topic }: { topic: TopicWritingTopic }) {
  return (
    <TopicPanel title={topic.task_type} eyebrow={`Writing Task ${topic.task}`}>
      <div className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Task Prompt
        </p>
        <p className="text-[15px] leading-7 text-foreground/90">{topic.prompt}</p>
      </div>

      {topic.practice_focus && (
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Practice Focus
          </p>
          <p className="text-[15px] leading-7 text-foreground/90">{topic.practice_focus}</p>
        </div>
      )}

      {topic.sample_outline && (
        <div className="border border-border bg-muted/30 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Sample Outline
          </p>
          <p className="mt-2 whitespace-pre-wrap text-[15px] leading-7 text-foreground/90">
            {topic.sample_outline}
          </p>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Planning Steps
          </p>
          <Checklist items={topic.planning_steps} />
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Structure Guide
          </p>
          <Checklist items={topic.structure_guide} />
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Key Vocabulary
        </p>
        <ChipRow items={topic.key_vocabulary} />
      </div>
    </TopicPanel>
  );
}

function ReadingTopicCard({ topic }: { topic: TopicReadingTopic }) {
  return (
    <TopicPanel title={topic.passage_theme} eyebrow={`Reading ${topic.difficulty}`}>
      {topic.passage_summary && (
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Passage Summary
          </p>
          <p className="text-[15px] leading-7 text-foreground/90">{topic.passage_summary}</p>
        </div>
      )}

      {topic.practice_focus && (
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Practice Focus
          </p>
          <p className="text-[15px] leading-7 text-foreground/90">{topic.practice_focus}</p>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Question Types
          </p>
          <ChipRow items={topic.question_types} />
        </div>
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Vocabulary
          </p>
          <ChipRow items={topic.vocabulary_hints} />
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Reading Strategy
        </p>
        <Checklist items={topic.strategy_steps} />
      </div>
    </TopicPanel>
  );
}

function ListeningTopicCard({ topic }: { topic: TopicListeningTopic }) {
  return (
    <TopicPanel title={topic.scenario} eyebrow={`Listening Section ${topic.section}`}>
      {topic.audio_context && (
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Audio Context
          </p>
          <p className="text-[15px] leading-7 text-foreground/90">{topic.audio_context}</p>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Question Types
          </p>
          <ChipRow items={topic.question_types} />
        </div>
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Vocabulary
          </p>
          <ChipRow items={topic.vocabulary_hints} />
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Listen For
          </p>
          <Checklist items={topic.listen_for} />
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Listening Strategy
          </p>
          <Checklist items={topic.strategy_steps} />
        </div>
      </div>
    </TopicPanel>
  );
}

export function RoadmapPhaseContent({ phase }: { phase: Phase }) {
  return (
    <div className="space-y-12">
      {phase.topics.speaking_topics.length > 0 && (
        <section className="space-y-5">
          <SectionHeader
            title="Speaking Practice"
            count={phase.topics.speaking_topics.length}
            icon={RiMicLine}
            bg={sectionMeta.speaking.bg}
            color={sectionMeta.speaking.color}
          />
          <div className="space-y-4">
            {phase.topics.speaking_topics.map((topic, index) => (
              <SpeakingTopicCard key={`${topic.topic}-${index}`} topic={topic} />
            ))}
          </div>
        </section>
      )}

      {phase.topics.writing_topics.length > 0 && (
        <section className="space-y-5">
          <SectionHeader
            title="Writing Practice"
            count={phase.topics.writing_topics.length}
            icon={RiEdit2Line}
            bg={sectionMeta.writing.bg}
            color={sectionMeta.writing.color}
          />
          <div className="space-y-4">
            {phase.topics.writing_topics.map((topic, index) => (
              <WritingTopicCard key={`${topic.task_type}-${index}`} topic={topic} />
            ))}
          </div>
        </section>
      )}

      {phase.topics.reading_topics.length > 0 && (
        <section className="space-y-5">
          <SectionHeader
            title="Reading Practice"
            count={phase.topics.reading_topics.length}
            icon={RiBookOpenLine}
            bg={sectionMeta.reading.bg}
            color={sectionMeta.reading.color}
          />
          <div className="space-y-4">
            {phase.topics.reading_topics.map((topic, index) => (
              <ReadingTopicCard key={`${topic.passage_theme}-${index}`} topic={topic} />
            ))}
          </div>
        </section>
      )}

      {phase.topics.listening_topics.length > 0 && (
        <section className="space-y-5">
          <SectionHeader
            title="Listening Practice"
            count={phase.topics.listening_topics.length}
            icon={RiHeadphoneLine}
            bg={sectionMeta.listening.bg}
            color={sectionMeta.listening.color}
          />
          <div className="space-y-4">
            {phase.topics.listening_topics.map((topic, index) => (
              <ListeningTopicCard key={`${topic.scenario}-${index}`} topic={topic} />
            ))}
          </div>
        </section>
      )}

      {phase.topics.study_plan_notes && (
        <div className="border border-border bg-muted/20 p-6">
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <RiStarLine className="h-5 w-5 text-primary" />
            How To Use This Roadmap
          </h3>
          <p className="text-[15px] leading-7 text-foreground/85">{phase.topics.study_plan_notes}</p>
        </div>
      )}
    </div>
  );
}

export function getPhaseTitle(num: number, result: TopicGeneratorResult): string {
  const titles: Record<number, string> = {
    1: "Foundation Roadmap",
    2: "Skill Builder",
    3: "Target Band Push",
    4: "Exam Readiness",
    5: "Final Polish",
  };

  if (titles[num]) return titles[num];
  if (result.weaknesses.length > 0) return `${result.weaknesses[0]} Focus`;
  return `Roadmap ${num}`;
}
