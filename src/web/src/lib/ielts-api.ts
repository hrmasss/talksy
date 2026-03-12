import { requestJson } from "./api-client";

export interface PlacementQuestion {
  thread_id: string;
  status: string;
  section: string;
  question_index: number;
  total_questions: number;
  question_text: string;
  question_type: string;
  options: string[];
  time_limit_seconds?: number | null;
  audio_url?: string | null;
}

export interface PlacementResult {
  thread_id: string;
  status: "completed";
  overall_band: number;
  listening_band: number;
  reading_band: number;
  writing_band: number;
  speaking_band: number;
  strengths: string[];
  weaknesses: string[];
  focus_areas: string[];
  feedback_markdown?: string | null;
}

export interface MockTestQuestion {
  thread_id: string;
  status: string;
  section: string;
  current_part: number;
  question_index: number;
  total_questions: number;
  question_text: string;
  question_type: string;
  options: string[];
  passage?: string | null;
  time_limit_seconds?: number | null;
  audio_url?: string | null;
}

export interface SectionScore {
  section: string;
  band_score?: number | null;
  detail?: string | null;
}

export interface MockTestReport {
  thread_id: string;
  status: "completed";
  section?: string | null;
  overall_band?: number | null;
  section_scores: SectionScore[];
  evaluations: Array<Record<string, unknown>>;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  final_report_markdown?: string | null;
}

export interface MockExamSession {
  thread_id: string;
  section: string;
  difficulty: string;
  status: string;
  question_index: number;
  total_questions: number;
  band_score?: number | null;
  section_scores: SectionScore[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  report_markdown?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface MockExamSessionListResponse {
  items: MockExamSession[];
}

export interface StudyActivity {
  id: string;
  section: string;
  activity_type: string;
  title: string;
  content: unknown;
  difficulty_level: number;
  is_completed: boolean;
  ai_feedback: Record<string, unknown>;
  band_score?: number | null;
}

export interface DailyStudyPlan {
  id: string;
  study_date: string;
  activities: StudyActivity[];
  completed_count: number;
  total_count: number;
  is_completed: boolean;
  ai_rationale?: string | null;
}

export interface DailyStudyHistoryResponse {
  items: DailyStudyPlan[];
}

export interface StudyActivityFeedback {
  activity_id: string;
  band_score?: number | null;
  feedback: Record<string, unknown>;
  is_correct?: boolean | null;
  suggestions: string[];
}

export interface ProgressScoreHistoryItem {
  date: string;
  overall_band?: number | null;
  listening?: number | null;
  reading?: number | null;
  writing?: number | null;
  speaking?: number | null;
}

export interface RecentScoreItem {
  date: string;
  band_score?: number | null;
  section?: string | null;
}

export interface ProgressOverview {
  current_estimated_band?: number | null;
  target_band_score?: number | null;
  days_until_exam?: number | null;
  total_tests_taken: number;
  total_activities_completed: number;
  section_scores: Record<string, number | null>;
  skill_profile: Record<string, unknown>;
  recent_scores: RecentScoreItem[];
  score_history: ProgressScoreHistoryItem[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

export interface TestHistoryItem {
  id: string;
  date: string;
  band_score?: number | null;
  section: string;
  feedback: Record<string, unknown>;
  ai_analysis: Record<string, unknown>;
}

export interface TestHistory {
  items: TestHistoryItem[];
  total: number;
}

export interface TopicSpeakingTopic {
  part: number | string;
  topic: string;
  cue_card?: string | null;
  questions: string[];
  vocabulary_hints: string[];
}

export interface TopicWritingTopic {
  task: number | string;
  task_type: string;
  prompt: string;
  sample_outline?: string | null;
  key_vocabulary: string[];
}

export interface TopicReadingTopic {
  passage_theme: string;
  difficulty: string;
  question_types: string[];
}

export interface TopicListeningTopic {
  section: number | string;
  scenario: string;
  question_types: string[];
}

export interface TopicGeneratorResult {
  estimated_band?: number | null;
  band_range?: string | null;
  section_estimates: Record<string, number | string | null>;
  strengths: string[];
  weaknesses: string[];
  assessment_summary?: string | null;
  speaking_topics: TopicSpeakingTopic[];
  writing_topics: TopicWritingTopic[];
  reading_topics: TopicReadingTopic[];
  listening_topics: TopicListeningTopic[];
  study_plan_notes?: string | null;
}

export function getProgress(userId: string): Promise<ProgressOverview> {
  return requestJson<ProgressOverview>(`/ielts/progress/${userId}`);
}

export function getDailyPlan(userId: string): Promise<DailyStudyPlan> {
  return requestJson<DailyStudyPlan>(`/ielts/study/daily/${userId}`);
}

export function getDailyPlanHistory(userId: string, days = 7): Promise<DailyStudyHistoryResponse> {
  const params = new URLSearchParams({ days: String(days) });
  return requestJson<DailyStudyHistoryResponse>(`/ielts/study/daily/history/${userId}?${params.toString()}`);
}

export function getDailyPlanById(userId: string, planId: string): Promise<DailyStudyPlan> {
  const params = new URLSearchParams({ user_id: userId });
  return requestJson<DailyStudyPlan>(`/ielts/study/daily/plan/${planId}?${params.toString()}`);
}

export function generateDailyPlan(userId: string): Promise<DailyStudyPlan> {
  return requestJson<DailyStudyPlan>(`/ielts/study/daily/generate/${userId}`, {
    method: "POST",
  });
}

export function submitActivityResponse(
  activityId: string,
  response: string,
  timeSpentSeconds = 0
): Promise<StudyActivityFeedback> {
  return requestJson<StudyActivityFeedback>("/ielts/study/submit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      activity_id: activityId,
      response,
      time_spent_seconds: timeSpentSeconds,
    }),
  });
}

export function startPlacementTest(
  userId: string,
  payload: {
    target_band_score?: number;
    exam_date?: string;
  }
): Promise<PlacementQuestion | PlacementResult> {
  return requestJson<PlacementQuestion | PlacementResult>(`/ielts/placement/start/${userId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function submitPlacementAnswer(
  threadId: string,
  answer?: string,
  audioBase64?: string
): Promise<PlacementQuestion | PlacementResult> {
  return requestJson<PlacementQuestion | PlacementResult>("/ielts/placement/answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      thread_id: threadId,
      answer,
      audio_base64: audioBase64,
    }),
  });
}

export function getActivePlacementTest(
  userId: string
): Promise<PlacementQuestion | PlacementResult | null> {
  return requestJson<PlacementQuestion | PlacementResult | null>(
    `/ielts/placement/active/${userId}`
  );
}

export function startMockTest(
  userId: string,
  payload: {
    test_type?: "full" | "section";
    section?: string;
    difficulty?: "beginner" | "intermediate" | "advanced" | "expert" | "adaptive";
  }
): Promise<MockTestQuestion> {
  return requestJson<MockTestQuestion>(`/ielts/mock-test/start/${userId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function submitMockAnswer(
  threadId: string,
  answer: string
): Promise<MockTestQuestion | MockTestReport> {
  return requestJson<MockTestQuestion | MockTestReport>("/ielts/mock-test/answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      thread_id: threadId,
      answer,
    }),
  });
}

export function getActiveMockTest(userId: string): Promise<MockExamSession | null> {
  return requestJson<MockExamSession | null>(`/ielts/mock-test/active/${userId}`);
}

export function listMockTestSessions(
  userId: string,
  options: {
    status?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<MockExamSessionListResponse> {
  const params = new URLSearchParams();
  if (options.status) {
    params.set("status", options.status);
  }
  if (options.limit != null) {
    params.set("limit", String(options.limit));
  }
  if (options.offset != null) {
    params.set("offset", String(options.offset));
  }

  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return requestJson<MockExamSessionListResponse>(`/ielts/mock-test/sessions/${userId}${suffix}`);
}

export function resumeMockTest(threadId: string): Promise<MockTestQuestion | MockTestReport> {
  const params = new URLSearchParams({ thread_id: threadId });
  return requestJson<MockTestQuestion | MockTestReport>(`/ielts/mock-test/resume?${params.toString()}`);
}

export function getTestHistory(
  userId: string,
  options: {
    limit?: number;
    offset?: number;
  } = {}
): Promise<TestHistory> {
  const params = new URLSearchParams();
  if (options.limit != null) {
    params.set("limit", String(options.limit));
  }
  if (options.offset != null) {
    params.set("offset", String(options.offset));
  }

  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return requestJson<TestHistory>(`/ielts/history/${userId}${suffix}`);
}

export function generateTopics(
  _userId: string,
  payload: {
    target_exam?: string;
    target_score?: number;
    current_level_description?: string;
    section_focus?: string;
    preferences?: Record<string, unknown>;
  }
): Promise<TopicGeneratorResult> {
  return requestJson<TopicGeneratorResult>("/practice/topics", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
