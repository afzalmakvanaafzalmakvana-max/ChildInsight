# ChildInsight — Product Requirements Document (PRD)

## 1. What to Build

**Product Name:** ChildInsight — Intelligent Learning & Development Guidance System
**Tagline:** Observe. Understand. Guide.

**One-line description:** ChildInsight is a data-driven educational platform that observes a
child's interaction with educational activities (activity choice, response accuracy, time
taken, attempts, engagement) and converts that interaction data into an understandable,
explainable learning profile and activity recommendations for parents and teachers.

**Core purpose (very important — repeat this everywhere in the app and in every AI prompt):**
- The system does **not** diagnose, label, or classify a child medically or psychologically.
- The system only observes activity interaction patterns and turns them into
  evidence-based, explainable educational insights.
- If a persistent concerning pattern is observed (e.g. very low engagement across almost
  everything, repeated abandonment, etc.), the system's language should gently suggest
  that the parent may want to discuss this with a qualified teacher/counsellor — it never
  says "your child has X condition."

**Core value flow:**
Child interacts with activity → system records session + event data → analytics engine
computes accuracy/engagement/consistency → learning pattern engine turns numbers into
plain-language observations → recommendation engine (rules + ML) suggests next activities
with a visible "why" → parent/teacher dashboards show all of this → progress is tracked
over time → periodic reports can be exported.

## 2. Targeted Users

| Role | Who they are | What they need |
|---|---|---|
| Child | The learner, typically pre-school to primary school age | Extremely simple, large-button, low-text, colourful interface to pick and play activities |
| Parent | Primary guardian of one or more children | A clear dashboard of their child's performance, engagement, strengths, practice areas, and recommendations |
| Teacher | Manages multiple assigned children/students | Class-wide and per-student view, ability to assign activities, no comparative ranking between children |
| Admin | Platform operator | Manage users, activities, categories, view system-wide analytics, audit logs |

## 3. Key Features (mapped to user problems)

- **Authentication & role-based access** — each role only sees what it's allowed to see.
- **Child profiles** — one parent can have multiple children.
- **Activity engine** — structured activities across categories (Visual, Logic, Numbers,
  Language, Memory), each with difficulty levels (Beginner → Easy → Medium → Advanced).
- **Session & event tracking** — every attempt, correct/incorrect answer, hint use, skip,
  completion or abandonment is logged.
- **Analytics engine** — turns raw sessions into accuracy, completion rate, consistency,
  engagement index, category-wise performance.
- **Learning Pattern Engine** — converts numeric metrics into plain-language observations
  ("Recent sessions show stronger engagement in visual and memory activities").
- **Recommendation engine** — 3 layers: rule-based → performance-based → personalized
  (rules + historical data + optional K-Means clustering), always with a visible reason.
- **Dashboards** — separate, purpose-built dashboards for Child / Parent / Teacher / Admin.
- **Reports** — weekly/monthly/custom, exportable as PDF/CSV, with a responsible-use notice.
- **Privacy & responsible-use safeguards** — minimum data collection, restricted access,
  no diagnostic language, clear responsible-use disclaimer on every report and on the
  landing page.

## 4. Explicit Non-Goals

- This is **not** a medical, psychological, or diagnostic tool.
- It does **not** rank or compare children against each other (teacher view especially).
- It does **not** assign personality types, IQ scores, or clinical labels.
- ML (K-Means) is used only to group *interaction patterns*, never to label a child.

## 5. Success Criteria (for a student/portfolio project)

- All 4 dashboards functional with real (or demo) data.
- At least 5 activity categories with 3+ difficulty levels each.
- Working analytics pipeline: session → features → metrics → insights.
- At least one working rule-based recommendation AND one ML-based (K-Means) pattern
  grouping, both showing a human-readable "why."
- Exportable PDF/CSV report with the responsible-use disclaimer.
- Clean, responsive, accessible UI — not "childish," professional-but-friendly.
