# ChildInsight — rules.md

## 1. What to Use

- Python 3.11+, Flask (application factory pattern, blueprints per role).
- SQLAlchemy ORM only — no raw SQL string concatenation, ever.
- Flask-Login for session auth; Werkzeug (`generate_password_hash` /
  `check_password_hash`) for passwords.
- Flask-WTF for forms + CSRF protection.
- Pandas/NumPy inside `app/services/` and `app/ml/` only — never inside route files.
- Scikit-learn `KMeans` for pattern grouping, always with a fixed `random_state`.
- Chart.js (CDN) for dashboard charts.
- Jinja2 templates with a shared `base.html` per role (child/parent/teacher/admin).

## 2. What to Avoid and Why

- No raw SQL / string-built queries → SQL injection risk.
- No storing plaintext passwords → obvious security failure.
- No client-side-only authorization checks → always re-check role/ownership server-side.
- No global "IQ / personality / diagnosis" labels anywhere in code, UI copy, or ML output
  → violates the project's core ethical constraint (see PRD §4).
- No child-facing screen with more than ~2 lines of text or dense tables → breaks the
  child UX requirement.
- No teacher-facing ranking/leaderboard across different children → replace with
  "Individual Progress" language only.
- Avoid heavy JS frameworks/build tooling unless explicitly requested — keep the project
  runnable with `python run.py` for easy academic demonstration.

## 3. Libraries & Dependencies

```
Flask
Flask-SQLAlchemy
Flask-Login
Flask-WTF
Flask-Migrate
Werkzeug
pandas
numpy
scikit-learn
reportlab        # or WeasyPrint, for PDF reports
python-dotenv
```
Pin versions in `requirements.txt` once chosen; keep it minimal — don't add a library
"just in case."

## 4. Error Handling

- Never show raw stack traces or DB errors to the user. Show:
  `"Something went wrong. Please try again."`
- Log the real exception (message, traceback, request path, user id if available) to a
  server-side log file — never log passwords, tokens, or full session cookies.
- Use Flask error handlers for 400/401/403/404/500 with friendly templates.
- Validate all incoming data server-side (types, ranges) before it touches the DB —
  e.g. `0 <= accuracy <= 100`, `attempts >= correct_answers`, `duration >= 0`.

## 5. Boundaries of AI (Antigravity / any AI coding agent working on this repo)

- The AI may generate code, models, routes, services, templates, and tests that match
  this spec (`PRD.md`, `architecture.md`, `phases.md`, `design.md`).
- The AI must **not** invent new diagnostic/medical language, new personally identifying
  data fields beyond what's specified, or new third-party integrations without being
  asked.
- The AI must **not** silently change the database schema across phases without
  updating `architecture.md` and `memory.md`.
- Before starting a new phase, the AI should read `memory.md` to see what's already
  done and what's in progress, and update it after finishing.
- If a requirement is ambiguous, the AI should make the smallest reasonable assumption,
  state it in `memory.md`, and continue — not block on it.

## 6. General Rules

- **Code style:** PEP8, 4-space indent, natural student-written style (clean, not over-engineered or textbook-perfect).
- **Comments:** Avoid excessive comments; only comment non-obvious logic. No AI boilerplate, "Note:" tags, or robotic explanations in code.
- **Naming:** Natural, slightly varied naming (`snake_case` for Python, `PascalCase` for model classes, table names plural lower-case, routes lower-case/kebab). Avoid repetitive generic names like `handleData` or `processInfo`.
- **Modularity:** Realistic structure — practical and clean without premature over-modularization.
- **Commits:** `feat:`, `fix:`, `refactor:`, `docs:`, `test:` prefixes; one logical change per commit.
- **Security & privacy:** role-based access enforced in every route (`@login_required` + ownership check); parent can only ever query their own children; teacher only their assigned children.
- **Performance:** paginate any list endpoint that can grow (sessions, events, students).
- **Docs/comments:** every service function gets a one-line docstring explaining the business rule it encodes (e.g. how the performance score is weighted).
- **Testing:** see `phases.md` Phase 9 — auth, activities, analytics, recommendations, and security each need at least a handful of tests before "done."
