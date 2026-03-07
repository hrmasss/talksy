"""Database table definitions using Piccolo ORM."""

from datetime import datetime
from enum import Enum

from piccolo.columns import (
    JSON,
    UUID,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    Text,
    Timestamp,
    Varchar,
)
from piccolo.columns.defaults.timestamp import TimestampNow
from piccolo.table import Table


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    USER = "user"


class ExamType(str, Enum):
    """Types of exams supported."""
    IELTS = "ielts"
    PTE = "pte"
    TOEFL = "toefl"


class ExamSection(str, Enum):
    """Exam sections/modules."""
    LISTENING = "listening"
    READING = "reading"
    WRITING = "writing"
    SPEAKING = "speaking"


class QuestionType(str, Enum):
    """Types of questions."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    MATCHING = "matching"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    SPEAKING = "speaking"


class User(Table):
    """User account table."""

    id = UUID(primary_key=True)
    email = Varchar(length=255, unique=True, index=True)
    password_hash = Varchar(length=255)
    full_name = Varchar(length=255)
    avatar_url = Varchar(length=500, null=True)
    role = Varchar(length=20, default=UserRole.USER, choices=UserRole)
    is_active = Boolean(default=True)
    is_verified = Boolean(default=False)
    target_exam = Varchar(length=50, null=True)  # ielts, pte, toefl
    target_score = Float(null=True)
    timezone = Varchar(length=100, default="UTC")
    preferences = JSON(default={})
    created_at = Timestamp(default=TimestampNow())
    updated_at = Timestamp(default=TimestampNow(), auto_update=datetime.now)
    last_login_at = Timestamp(null=True)

    # IELTS-specific profile fields
    target_band_score = Float(null=True)
    exam_date = Date(null=True)
    preferred_daily_practice_time = Integer(null=True)  # minutes
    current_estimated_band = Float(null=True)
    skill_profile = JSON(default={})  # {strengths: [], weaknesses: [], focus_areas: []}
    onboarding_completed = Boolean(default=False)
    section_scores = JSON(default={})  # {listening: 0, reading: 0, writing: 0, speaking: 0}


class Exam(Table):
    """Exam/test definition table."""

    id = UUID(primary_key=True)
    exam_type = Varchar(length=50, index=True)  # ielts, pte, toefl
    title = Varchar(length=255)
    description = Text(null=True)
    section = Varchar(length=50, index=True)  # listening, reading, writing, speaking
    duration_minutes = Integer()
    total_questions = Integer()
    instructions = Text(null=True)
    difficulty_level = Integer(default=1)  # 1-5
    is_active = Boolean(default=True)
    is_free = Boolean(default=False)
    metadata = JSON(default={})
    created_at = Timestamp(default=TimestampNow())
    updated_at = Timestamp(default=TimestampNow(), auto_update=datetime.now)


class Question(Table):
    """Question bank table."""

    id = UUID(primary_key=True)
    exam = ForeignKey(references=Exam)
    question_type = Varchar(length=50)  # multiple_choice, fill_blank, etc.
    question_number = Integer()
    question_text = Text()
    question_audio_url = Varchar(length=500, null=True)
    question_image_url = Varchar(length=500, null=True)
    options = JSON(default=[])  # For multiple choice questions
    correct_answer = JSON()  # Can be string, list, or dict
    explanation = Text(null=True)
    points = Float(default=1.0)
    time_limit_seconds = Integer(null=True)
    hints = JSON(default=[])
    tags = JSON(default=[])
    created_at = Timestamp(default=TimestampNow())


class ExamAttempt(Table):
    """User exam attempt tracking."""

    id = UUID(primary_key=True)
    user = ForeignKey(references=User)
    exam = ForeignKey(references=Exam)
    started_at = Timestamp(default=TimestampNow())
    completed_at = Timestamp(null=True)
    time_spent_seconds = Integer(default=0)
    score = Float(null=True)
    max_score = Float(null=True)
    band_score = Float(null=True)  # For IELTS-style scoring
    status = Varchar(length=50, default="in_progress")  # in_progress, completed, abandoned
    feedback = JSON(default={})
    ai_analysis = JSON(default={})
    created_at = Timestamp(default=TimestampNow())


class Answer(Table):
    """User answer to a question."""

    id = UUID(primary_key=True)
    attempt = ForeignKey(references=ExamAttempt)
    question = ForeignKey(references=Question)
    user_answer = JSON()  # Can be string, list, or dict
    audio_response_url = Varchar(length=500, null=True)  # For speaking answers
    is_correct = Boolean(null=True)
    points_earned = Float(default=0.0)
    time_spent_seconds = Integer(default=0)
    ai_feedback = JSON(default={})
    created_at = Timestamp(default=TimestampNow())


class ConversationSession(Table):
    """Conversation practice session."""

    id = UUID(primary_key=True)
    user = ForeignKey(references=User)
    topic = Varchar(length=255)
    scenario = Text(null=True)
    difficulty_level = Integer(default=1)  # 1-5
    started_at = Timestamp(default=TimestampNow())
    ended_at = Timestamp(null=True)
    duration_seconds = Integer(default=0)
    message_count = Integer(default=0)
    vocabulary_used = JSON(default=[])
    grammar_score = Float(null=True)
    fluency_score = Float(null=True)
    coherence_score = Float(null=True)
    overall_score = Float(null=True)
    ai_summary = Text(null=True)
    ai_suggestions = JSON(default=[])
    created_at = Timestamp(default=TimestampNow())


class ConversationMessage(Table):
    """Individual message in a conversation."""

    id = UUID(primary_key=True)
    session = ForeignKey(references=ConversationSession)
    role = Varchar(length=50)  # user, assistant
    content = Text()
    audio_url = Varchar(length=500, null=True)
    timestamp = Timestamp(default=TimestampNow())
    analysis = JSON(default={})  # Grammar, vocabulary analysis


# ──────────────────────────────────────────────────────────────────
# IELTS Placement / Onboarding
# ──────────────────────────────────────────────────────────────────

class PlacementTest(Table):
    """Initial diagnostic placement test record."""

    id = UUID(primary_key=True)
    user = ForeignKey(references=User)
    status = Varchar(length=50, default="in_progress")  # in_progress, completed
    started_at = Timestamp(default=TimestampNow())
    completed_at = Timestamp(null=True)

    # Section scores (0-9 IELTS band)
    listening_band = Float(null=True)
    reading_band = Float(null=True)
    writing_band = Float(null=True)
    speaking_band = Float(null=True)
    overall_band = Float(null=True)

    # AI analysis results
    skill_profile = JSON(default={})  # {strengths: [], weaknesses: [], focus_areas: []}
    ai_analysis = JSON(default={})
    responses = JSON(default={})  # Raw Q&A for each section
    thread_id = Varchar(length=255, null=True)  # LangGraph thread


class PlacementResponse(Table):
    """Individual response within a placement test."""

    id = UUID(primary_key=True)
    placement_test = ForeignKey(references=PlacementTest)
    section = Varchar(length=50, index=True)  # listening, reading, writing, speaking
    question_text = Text()
    question_type = Varchar(length=50)  # multiple_choice, fill_blank, essay, speaking
    user_answer = Text()
    ai_evaluation = JSON(default={})
    band_score = Float(null=True)
    created_at = Timestamp(default=TimestampNow())


# ──────────────────────────────────────────────────────────────────
# Daily Study Content
# ──────────────────────────────────────────────────────────────────

class DailyStudyPlan(Table):
    """AI-generated daily study plan for a user."""

    id = UUID(primary_key=True)
    user = ForeignKey(references=User)
    study_date = Date()
    activities = JSON(default=[])  # [{type, section, title, content, difficulty, ...}]
    completed_count = Integer(default=0)
    total_count = Integer(default=0)
    is_completed = Boolean(default=False)
    ai_rationale = Text(null=True)  # Why these activities were chosen
    created_at = Timestamp(default=TimestampNow())


class StudyActivity(Table):
    """Individual study activity within a daily plan."""

    id = UUID(primary_key=True)
    daily_plan = ForeignKey(references=DailyStudyPlan)
    user = ForeignKey(references=User)
    section = Varchar(length=50, index=True)  # listening, reading, writing, speaking, vocabulary
    activity_type = Varchar(length=50)  # vocabulary, mini_listening, reading_passage, speaking_prompt, writing_task
    title = Varchar(length=255)
    content = JSON(default={})  # The actual exercise content
    difficulty_level = Integer(default=1)  # 1-5
    is_completed = Boolean(default=False)
    user_response = JSON(default={})
    ai_feedback = JSON(default={})
    band_score = Float(null=True)
    time_spent_seconds = Integer(default=0)
    created_at = Timestamp(default=TimestampNow())
    completed_at = Timestamp(null=True)


# ──────────────────────────────────────────────────────────────────
# Progress Tracking
# ──────────────────────────────────────────────────────────────────

class ProgressSnapshot(Table):
    """Periodic snapshot of user's IELTS progress."""

    id = UUID(primary_key=True)
    user = ForeignKey(references=User)
    snapshot_date = Date()
    overall_band = Float(null=True)
    listening_band = Float(null=True)
    reading_band = Float(null=True)
    writing_band = Float(null=True)
    speaking_band = Float(null=True)
    tests_taken = Integer(default=0)
    activities_completed = Integer(default=0)
    strengths = JSON(default=[])
    weaknesses = JSON(default=[])
    ai_recommendations = JSON(default=[])
    created_at = Timestamp(default=TimestampNow())
