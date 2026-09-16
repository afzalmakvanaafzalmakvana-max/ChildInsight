# ChildInsight — phases.md

Each phase should be given to Google Antigravity (or any AI coding agent) as **one prompt**,
one at a time, only after the previous phase is verified working. Update `memory.md` at the
end of every phase.

## Phase 1 — Project Foundation
- Flask app factory + blueprints skeleton (auth, parent, teacher, child, admin, api)
- Config (`config.py`, `.env`) for dev/prod
- Database setup (SQLAlchemy + Flask-Migrate) with `users` and `children` models
- Authentication: register, login, logout, password hashing, role field
- Base templates per role + a minimal landing page
- `requirements.txt`, `README.md`

## Phase 2 — User Management
- Parent: create/edit/view own children
- Teacher: view assigned children (via a `teacher_assignments` table)
- Admin: manage users (activate/deactivate, change role)
- Role-based route protection (decorator/utility checking `current_user.role` +
  ownership of the target child)

## Phase 3 — Activity Engine
- `categories`, `activities`, `activity_questions` models
- Seed script with 5 categories × 3–4 difficulty levels × a handful of questions each
- Child-facing "pick an activity" screen (large buttons, category icons)
- Activity player: show question, capture answer, score it, move to next

## Phase 4 — Data Collection
- `activity_sessions` (start/end, duration, attempts, correct, accuracy, status)
- `interaction_events` (started, question_viewed, answer_selected, correct, incorrect,
  hint_used, skipped, completed, abandoned)
- Session and event writes happen from the activity player in real time

## Phase 5 — Analytics
- `services/analytics_service.py`: Pandas pipeline turning sessions/events into
  accuracy, completion rate, consistency, category aggregates
- `services/engagement_service.py`: engagement index from completion, repeat
  participation, frequency, voluntary selection, time spent, abandonment, retries
- `progress_records` populated on a schedule (or on-demand) per child/category

## Phase 6 — Recommendation Engine
- Rule-based layer (`IF accuracy >= 80 THEN level-up`, etc.)
- Performance-based layer (adjust difficulty from recent accuracy/completion)
- Personalized layer combining history + category performance
- Every recommendation stores a `reason` string — always shown in the UI

## Phase 7 — Machine Learning
- `ml/features.py`: build the feature vector per child (visual/memory/logic/number/
  language/engagement scores)
- `ml/clustering.py`: K-Means over these features → "pattern group" labels like
  "Visual + Memory Strong Interaction" (never a personality/IQ label)
- Wire cluster output into the Learning Pattern Engine's plain-language observations

## Phase 8 — Dashboards & Reports
- Parent dashboard: summary cards, category chart, trend chart, recommendations,
  recent sessions
- Teacher dashboard: student list (no ranking), individual student profile, assign
  activity, class-wide analytics
- Admin dashboard: system overview, users/children/activities management, analytics
- PDF/CSV report generation with the responsible-use disclaimer on every report

## Phase 9 — Security & Polish
- CSRF protection on all forms, input validation everywhere data enters the system
- Friendly error pages (400/401/403/404/500), loading states, empty states
- Audit log (`user_id, action, target_type, target_id, timestamp`) for admin/teacher
  write actions
- Responsive layout pass (mobile/tablet/desktop), accessibility pass (labels, contrast,
  focus states, alt text)
- Tests: auth, activities, analytics, recommendations, security (see `rules.md` §6)

## Phase 10 — Deployment
- Production config (env vars, secret key, DB URL)
- Migration to MySQL/PostgreSQL if needed
- HTTPS, logging, basic backup plan
- Demo data seed clearly labelled "Demo Data" in the UI
