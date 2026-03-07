Create an **AI-powered IELTS preparation platform** that helps users maximize their IELTS score through adaptive learning, personalized practice, and AI-generated mock tests.

The system must support the four IELTS modules:

• Listening 🎧
• Reading 📖
• Writing ✍️
• Speaking 🗣️

The goal is to continuously analyze user performance and generate personalized study content and mock tests that improve the user's weaknesses over time.

---

### 1. User Authentication

Users must create an account and log in.

Each user profile should contain:

* target_band_score
* exam_date
* preferred_daily_practice_time
* current_estimated_band
* skill_profile
* onboarding_completed (boolean field)

The **onboarding_completed field** determines whether the user has completed the initial diagnostic test.

If onboarding_completed = false, the user must complete the **Initial Placement Test** before accessing the platform.

---

### 2. Onboarding Flow (Initial Placement Test)

After login, if onboarding_completed is false, the user must take a **short diagnostic test**.

Each IELTS section must have a **3–5 minute mini test**:

Listening Test (3–5 minutes)

* Short audio scenario
* 2–3 questions
* Multiple choice or fill in the blank

Reading Test (3–5 minutes)

* Short passage
* 3–4 comprehension questions

Writing Test (3–5 minutes)

* Short IELTS-style prompt
* 100–150 word response

Speaking Test (3–5 minutes)

* 2–3 speaking questions
* User records a short answer

Purpose of this test:
Quickly estimate the user's current English ability.

---

### 3. AI Evaluation of Initial Test

The AI should evaluate the responses and generate:

Estimated IELTS Band Score

Section scores:

* Listening band
* Reading band
* Writing band
* Speaking band

AI must analyze:

* grammar accuracy
* vocabulary range
* comprehension ability
* coherence
* fluency (for speaking)

Example output:

Estimated Band: 5.5

Listening: 6.0
Reading: 5.5
Writing: 5.0
Speaking: 5.5

The result should also generate a **skill profile**.

Example skill profile:

Strengths:

* listening comprehension
* basic reading ability

Weaknesses:

* grammar accuracy
* academic vocabulary
* writing structure
* speaking fluency

After this evaluation, the system must set:

onboarding_completed = true

---

### 4. Personalized Learning Profile

Based on the placement test results, generate a **user learning profile** that identifies:

* strengths
* weaknesses
* recommended study focus

Example:

Focus Areas:

* Writing Task 2 structure
* Vocabulary expansion
* Speaking fluency

This profile will guide all future learning content and mock tests.

---

### 5. Daily AI Study Content

Each day the system generates personalized learning activities such as:

* vocabulary practice
* mini listening exercise
* reading passage with questions
* speaking prompt
* writing task

The difficulty should gradually increase toward the user's target band score.

---

### 6. Mock Test Generation

Users can start a practice test at any time.

Tests can be:

* full IELTS mock test
* section specific test (Listening, Reading, Writing, Speaking)

The system must dynamically generate tests based on:

* user current level
* weak areas
* target band score
* past performance

---

### 7. Use Previous Test History

Before generating any new test or exercise, the AI must receive the user's **last 10 test results**.

Example input context:

User Target Band: 7.0
Current Estimated Band: 5.5

Last 10 Test Results:
Test 1
Listening: 6.0
Reading: 5.5
Writing: 5.0
Speaking: 5.5

Test 2
Listening: 6.5
Reading: 6.0
Writing: 5.5
Speaking: 5.5

Weakness Patterns:

* writing task structure
* grammar accuracy
* speaking fluency

The AI must use this context to:

* adjust difficulty
* focus on weak areas
* avoid repeating similar questions
* improve learning progression

---

### 8. AI Test Generation Rules

The AI should behave like an **IELTS expert instructor and exam generator**.

Instructions:

1. Generate realistic IELTS-style questions.
2. Focus more on the user's weak areas.
3. Gradually increase difficulty toward the target band score.
4. Follow official IELTS question patterns.

Section rules:

Listening

* real-world scenario
* multiple choice or fill in blank

Reading

* short academic passage
* comprehension questions

Writing

* Task 1 or Task 2 prompt
* academic or general training style

Speaking

* Part 1 personal questions
* Part 2 cue card
* Part 3 discussion questions

---

### 9. AI Evaluation of User Answers

When a user submits answers, the AI must evaluate using **IELTS band descriptors**.

For writing and speaking evaluation consider:

* Task achievement
* Coherence and cohesion
* Lexical resource
* Grammar range and accuracy

Return:

Overall Band Score
Section Band Score
Detailed Feedback
Improvement Suggestions

Example output:

Writing Band: 5.5

Feedback:

* Good idea development but limited vocabulary
* Grammar mistakes in complex sentences
* Improve paragraph structure

Suggestion:
Practice linking words and academic vocabulary.

---

### 10. Progress Tracking

The platform must store all test results.

Provide analytics such as:

* band score history
* improvement trends
* weak skills
* performance per section

Example dashboard:

Listening Progress
Reading Progress
Writing Progress
Speaking Progress

Band score trend over time.

---

### 11. Adaptive Learning Logic

The AI must continuously adapt the learning experience.

Rules:

* If a user repeatedly scores low in one section, increase practice for that section.
* If a user improves consistently, increase difficulty.
* If the user approaches their target band score, simulate full IELTS exams.

The platform should behave like a **personal AI IELTS tutor** that adjusts learning strategies automatically.
