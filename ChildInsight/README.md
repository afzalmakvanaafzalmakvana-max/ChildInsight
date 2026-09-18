# ChildInsight — Intelligent Learning & Development Guidance System

> **Observe. Understand. Guide.**

ChildInsight is an educational platform designed to observe children's interactions with educational activities (choice, response accuracy, duration, attempts, hint engagement) and convert that data into understandable, explainable learning profiles and tailored recommendations for parents and educators.

---

### 🛡️ Ethical Mandate & Responsible-Use Notice (PRD §4)

- **Non-Diagnostic:** ChildInsight does **not** diagnose, label, or classify a child medically or psychologically. It does not output medical categorizations, psychiatric indicators, or developmental disorder labels.
- **Explainable Guidance:** All recommendations display human-readable educational rationales (e.g. *"Demonstrated 85% accuracy in beginner visual puzzles; ready for multi-step pattern matching"*).
- **Non-Comparative:** Classroom and teacher views strictly celebrate individual growth. There are **zero cross-student rankings, leaderboards, or score comparisons**.
- **Strength-Based Framing:** Profiles emphasize what children do well and where additional supportive practice can build confidence.

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- **Python:** 3.11 or higher
- **Git**
- **pip** and **virtualenv**

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone https://github.com/your-org/childinsight.git
cd ChildInsight

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to create your local `.env`:
```bash
cp .env.example .env
```
*(By default, `.env` is configured to use local SQLite with development settings — zero additional database setup required).*

### 4. Run Database Migrations
Apply all schema revisions (users, children, activities, questions, sessions, events, recommendations, audit logs):
```bash
python -m flask --app run.py db upgrade
```

### 5. Seed Demo Data
Pre-load a complete educational environment with 5 categories, 115 interactive activities, 415 questions, demo users across all roles, 3 children, 18 realistic activity sessions, trained K-Means pattern clustering, and tailored recommendations:
```bash
python -m flask --app run.py seed-demo
```
*(All seeded demo entities are clearly marked with a `Demo Data` badge throughout the parent, teacher, and child user interfaces).*

### 6. Run the Development Server
```bash
python run.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## 🔑 Demo Login Accounts

After running `python -m flask --app run.py seed-demo`, you can log into any portal using the following verified credentials:

| Role | Email Address | Password | Portal Features |
|---|---|---|---|
| **Platform Admin** | `admin@childinsight.demo` | `DemoPass123!` | System metrics, user management, educator assignment, security audit logs |
| **Educator / Teacher** | `teacher@childinsight.demo` | `DemoPass123!` | Student roster, individual growth profiles, class-wide aggregates (strictly unranked) |
| **Parent / Guardian** | `parent@childinsight.demo` | `DemoPass123!` | Performance cards, trend charts, tailored recommendations, PDF/CSV reports |

*To test the child play experience, log in as Parent Jordan and launch any activity from the dashboard, or navigate directly to `/child/select-child`.*

### 🔑 Password Reset & Demo Mode
ChildInsight includes a secure "Forgot Password" workflow adhering to zero user enumeration principles:
- Accessible via the **"Forgot password?"** link on the login page (`/login` or directly at `/forgot-password`).
- Submitting any email produces the same neutral confirmation message (*"If an account exists for this email address, password reset instructions have been generated."*) to prevent user enumeration attacks.
- **Demo Mode (Simulated Email Delivery)**: Because no SMTP server is configured in local development/demo environments, entering a registered email (e.g., `parent@childinsight.demo`) creates a secure 30-minute token, logs the link in the server log, and presents an amber callout box directly on-screen with the reset link.
- Reset tokens are single-use, expire after 30 minutes, and are stored hashed (SHA-256) in the `password_reset_tokens` table.

---

## 🌐 Multilingual Architecture & Language Support (i18n)

ChildInsight features a lightweight, robust internationalization (i18n) system that directly connects a child's **Preferred Language** profile setting to their learning experience in the Child Activity Zone (`/child/*`).

### Supported vs. Coming Soon Languages

| Language | Code | Support Status | Experience |
|---|---|---|---|
| **English** | `en` | **Fully Supported** | Full UI, activity prompts, questions, options, hints, and feedback in English. |
| **Hindi** | `hi` | **Fully Supported** | Full UI, category domains, seed activities, randomized options, hints, praise, and feedback in Hindi (Devanagari). |
| **Spanish** | `es` | *Coming Soon* | Selectable in child profile dropdown with `(Coming Soon)`. Gracefully falls back to English. |
| **French** | `fr` | *Coming Soon* | Selectable in child profile dropdown with `(Coming Soon)`. Gracefully falls back to English. |
| **German** | `de` | *Coming Soon* | Selectable in child profile dropdown with `(Coming Soon)`. Gracefully falls back to English. |
| **Mandarin** | `zh` | *Coming Soon* | Selectable in child profile dropdown with `(Coming Soon)`. Gracefully falls back to English. |

> **Graceful Fallback:** If a Hindi-preferred child encounters an activity that has not yet been translated, the activity content renders in English with a gentle notice banner:
> *🌐 अंग्रेजी में दिखाया जा रहा है — हिंदी संस्करण जल्द ही आ रहा है* (*"Showing in English — Hindi version coming soon"*).

---

### How Content Translations Are Stored

Translations are stored alongside original activity records using SQLite/PostgreSQL-compatible JSON columns:

1. **`activities.translations_json`**:
   ```json
   {
     "hi": {
       "title": "रंग मिलाओ साहसिक खोज [Demo Data]",
       "description": "जादुई रंगों को मिलाने और प्रकृति में आकृतियों को पहचानने में चित्रकार की मदद करें!"
     }
   }
   ```
2. **`activity_questions.translations_json`**:
   ```json
   {
     "hi": {
       "question_text": "जब आप चमकीले पीले और लाल रंग को एक साथ मिलाते हैं, तो कौन सा जादुई नया रंग बनता है?",
       "options": ["नारंगी", "नीला", "हरा", "बैंगनी"],
       "answer": "नारंगी",
       "hint": "एक रसीले संतरे या कद्दू के बारे में सोचें!"
     }
   }
   ```

### Dynamic Model Getters

Model helper methods automatically resolve the child's active language with fallback to English:
- `activity.get_title(lang)`: Returns translated title or default English title.
- `activity.get_description(lang)`: Returns translated description or default English description.
- `activity.has_translation(lang)`: Checks if a translation payload exists for the target language.
- `question.get_question_text(lang)`: Returns translated question prompt.
- `question.get_options(lang)`: Returns translated list of answer options.
- `question.get_shuffled_options(lang)`: Returns randomized translated options for display.
- `question.get_correct_answer(lang)`: Returns translated correct answer for evaluation.
- `question.get_hint(lang)`: Returns translated learning hint.

---

### How to Add a New Language

To introduce full support for a new language (e.g., Spanish `es`):

1. **Add Translation Dictionary**:
   Create `app/translations/es.py` defining the UI dictionary `TRANSLATIONS`:
   ```python
   TRANSLATIONS = {
       'explore': 'Explorar →',
       'play_now': 'Jugar Ahora →',
       'back_to_categories': '← Volver a Categorías',
       'lets_learn_play': '¡Vamos a Aprender y Jugar!',
       ...
   }
   ```
2. **Register Language in `app/translations/__init__.py`**:
   - Move `'es': 'Spanish'` from `COMING_SOON_LANGUAGES` to `SUPPORTED_LANGUAGES`.
   - Update `normalize_language()` to map `'es'`, `'spanish'`, `'español'` to `'es'`.
   - Update `get_translations()` to return `ES_TRANSLATIONS` when `lang == 'es'`.
3. **Update Child Form Dropdown (`app/forms/child.py`)**:
   Remove `(Coming Soon)` from the choice label: `('Spanish', 'Spanish')`.
4. **Seed Content Translations**:
   Populate `translations_json` with `"es"` payloads on target activities and questions.

---

## 🤝 Parent-Initiated Teacher Access & Dual Educator Architecture

ChildInsight features a dual-channel educator access architecture designed to balance institutional administration with parent-directed learning support:

```
Institutional Channel (Top-Down)       Parent-Directed Channel (Bottom-Up)
┌────────────────────────────────┐     ┌────────────────────────────────┐
│  Platform Admin / School Lead   │     │  Parent / Primary Guardian     │
│  (/admin/assignments)          │     │  (/parent/children/<id>#share) │
└───────────────┬────────────────┘     └───────────────┬────────────────┘
                │                                      │
                ▼                                      ▼
     [teacher_assignments]                   [child_teacher_access]
      Status: Permanent admin pairing         Status: pending → active / declined / revoked
                │                                      │
                └───────────────────┬──────────────────┘
                                    ▼
                 Unified Educator Access Layer
                 - @child_access_required(write=False)
                 - Classroom Roster & Dashboard
                 - Full Progress Reports (PDF / CSV)
                 - Tailored Activity Assignments
```

### How Parent-Initiated Access Differs From & Coexists With Admin Assignments

| Dimension | Admin-Managed Assignments (`teacher_assignments`) | Parent-Initiated Access (`child_teacher_access`) |
|---|---|---|
| **Initiator** | Platform Administrator or School Operator | Parent / Primary Guardian |
| **Use Case** | Institutional classroom assignments (homeroom teachers, school terms) | Tutoring, after-school educators, external specialists, or parent-chosen teachers |
| **Consent Model** | Administrative directive (immediate access upon creation) | **Explicit Teacher Consent Required**: Teacher receives pending invite and must click **Accept** before viewing student data |
| **Revocation** | Removed by Platform Admin | Revocable at any time by the **Parent** or by the **Platform Admin** (instant HTTP 403 enforcement) |
| **Multiplicity** | Multiple teachers per child, multiple students per teacher | Multiple teachers per child, multiple students per teacher (zero artificial limits) |
| **Coexistence** | Evaluated via boolean OR: a teacher gains access if an active record exists in **either** system |

### Key Feature Workflows

1. **Child Card Direct Quick Action**:
   - On the parent's child list screen (`/parent/children`), each child card features a **"Share with Teacher"** button directly alongside "View Profile" and "Edit".
   - Clicking the button jumps directly to the `#share-with-teacher` flow for that specific learner without having to manually locate the section.
   - Styled consistently (`btn btn-outline btn-sm`) and configured with responsive flex-wrapping (`flex-wrap: wrap; gap: 0.5rem;`) so buttons wrap cleanly on mobile screens without card distortion.
2. **Parent Invite Flow & Anti-Enumeration Protection**:
   - Parents invite an educator by entering their email address in the child detail page.
   - **Zero Account Enumeration**: If the email does not correspond to an active teacher account, the system outputs: *"No active teacher account found with this email."* It strictly avoids disclosing whether the email exists under a different role (e.g. parent or child).
   - **Anti-Spam Rate-Limiting**: Duplicate pending requests for the same child-teacher pair are blocked with an informative prompt.
3. **Teacher Consent & In-Dashboard Requests**:
   - The teacher's dashboard displays a dedicated **"Pending Student Access Requests"** card highlighting requests (*"Parent Alice has requested you view Leo's report"*).
   - **Accept**: Moves grant status to `active`, registers student in teacher's roster, and notifies the parent.
   - **Decline**: Moves grant status to `declined`, notifies parent, and grants zero student access.
4. **Administrative Oversight & Transparency**:
   - The Admin Assignments page (`/admin/assignments#parent-grants` or `/admin/teacher-access`) provides platform-wide transparency over all active, pending, declined, and revoked parent grants.
   - Administrators can review the audit history and revoke any grant if necessary with full audit tracing.
5. **Security & Audit Logging**:
   - Every lifecycle event (`parent_grant_teacher_access_invite`, `teacher_accept_access_request`, `teacher_decline_access_request`, `parent_revoke_teacher_access`, `admin_revoke_parent_teacher_access`) writes an immutable record to `audit_logs`.
   - Revocation takes effect immediately at the database query and decorator level (`@child_access_required`), instantly barring the educator from student reports and analytics endpoints.

---

## 🧪 Automated Testing

ChildInsight includes a comprehensive unit and integration test suite across all 10 phases, administrative subsystems, UI bug fixes, and internal agent flows (190 automated tests):

```bash
# Run the full regression test suite (all 190 tests)
python -m unittest discover tests

# Run specific agent, phase, UI, or security test suites
python -m unittest tests.test_child_ui_fixes
python -m unittest tests.test_content_suggestions
python -m unittest tests.test_agents
python -m unittest tests.test_admin_activities
python -m unittest tests.test_admin_categories
python -m unittest tests.test_forgot_password
python -m unittest tests.test_phase10
python -m unittest tests.test_phase9
python -m unittest tests.test_phase7
python -m unittest tests.test_phase6
```

---

## 📡 REST API & Interactive Documentation

ChildInsight features a clean, decoupled REST API surface under `/api/` designed for external clients, future mobile applications, and learning analytics integrations.

- 📖 **Full API Reference**: Complete parameter, authorization, request body, and response schema specifications are documented in [docs/API.md](docs/API.md).
- ⚡ **Interactive API Explorer**: A zero-build-tool, browser-accessible Swagger UI explorer is available at:
  ```
  http://localhost:5000/api/docs
  ```
- 📄 **OpenAPI Specification**: Machine-readable OpenAPI 3.0.3 specification is served directly at:
  ```
  http://localhost:5000/api/openapi.json
  ```

### Quick Endpoint Reference

| Method | Route | Auth / Role | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | System status and service health check |
| `GET` | `/api/auth/status` | Public | Current user authentication state & identity |
| `GET` | `/api/children` | Parent, Teacher, Admin | List authorized children profiles |
| `GET` | `/api/children/<id>` | Parent, Assigned Teacher, Admin | Retrieve individual child record |
| `GET` | `/api/activities` | Public | Catalog of active educational activities |
| `GET` | `/api/activities/<id>` | Public | Activity details and question sequence |
| `POST` | `/api/sessions` | Parent, Assigned Teacher, Admin | Initialize interactive learning session |
| `GET` | `/api/sessions/<id>` | Parent, Assigned Teacher, Admin | Retrieve session record & telemetry events |
| `GET` | `/api/analytics/<child_id>` | Parent, Assigned Teacher, Admin | Computed analytics & category mastery |
| `GET` / `POST` | `/api/progress/<child_id>` | Parent, Assigned Teacher, Admin | Category progress records & recalculation |
| `GET` | `/api/recommendations/<child_id>` | Parent, Assigned Teacher, Admin | Algorithmic activity recommendations |
| `GET` | `/api/notifications` | Authenticated Users | In-dashboard alerts & unread counter |
| `POST` | `/api/notifications/<id>/read` | Notification Recipient | Mark individual alert as read |
| `POST` | `/api/notifications/mark-all-read` | Authenticated Users | Mark all user alerts as read |

All `/api/` endpoints are CSRF-exempt (`csrf.exempt(api_bp)`), authenticate via session cookies, and return JSON responses.

---

## 📊 Sample Outputs (PDF & CSV Reports)

For demonstration, evaluation, and presentation purposes, pre-generated sample educational progress reports for a demo child (**Leo**, age 6) are stored directly in the `docs/` folder and can be inspected without running the application:

- 📄 **Sample PDF Progress Report**: [`docs/sample-report.pdf`](docs/sample-report.pdf) — Professional, printable multi-section report compiled with ReportLab (`reportlab.rl_config.pageCompression = 0`) featuring:
  - Learner profile metadata (name, age, grade, language)
  - Overall analytics summary (accuracy, completion rate, consistency score, engagement index, composite score)
  - Machine learning interaction pattern observation (K-Means cluster mapping)
  - Category breakdown across all 5 cognitive domains
  - Detailed chronological session log with duration, attempts, and accuracy
  - Tailored, explainable recommendations (priority, activity title, level-up/reinforce reason)
  - PRD §4 mandatory ethical responsible-use disclaimer
- 📈 **Sample CSV Data Export**: [`docs/sample-report.csv`](docs/sample-report.csv) — Structured comma-separated export suitable for spreadsheet tools (Microsoft Excel, Google Sheets, LibreOffice Calc) or educational data pipelines containing all profile attributes, metrics, session history, and recommendations.

---

## 🤖 Internal System Agents & Platform Health

ChildInsight incorporates an internal agent layer under `app/agent/` designed to keep the platform reliable, ethically compliant, multilingual-aware, and self-maintaining without manual administrator intervention.

> [!NOTE]
> **Architecture & Transparency Disclosure**: ChildInsight's internal agents are **deterministic rule-based monitors, schema validators, multilingual content inspectors, and scheduled machine learning pipelines** working in coordination. They do not claim or constitute Artificial General Intelligence (AGI), autonomous self-awareness, or black-box clinical decision-making. Every educational suggestion and draft is strictly pending until reviewed and approved by a human administrator.

### 1. Safety & Compliance Agent (`compliance_agent.py`)
- **What it does:** Acts as an ethical language sentinel. Scans generated recommendation reasons, notification alerts, exported reports, and **Hindi content translations** before anything is saved or presented to parents, teachers, or learners.
- **Bilingual Clinical Blacklist:** PRD §4 strictly bans clinical, psychiatric, and diagnostic terminology. The agent enforces equivalent, linguistically verified blacklists across **both English and Hindi (Devanagari)**:
  - *English:* `adhd`, `autism`, `dyslexia`, `disorder`, `syndrome`, `deficit`, `abnormal`, `impaired`, `pathology`, `iq`, `retarded`, `handicap`, `clinical`, `diagnosis`, `medical`, etc.
  - *Hindi:* विकार (*disorder*), संलक्षण/सिंड्रोम (*syndrome*), निदान (*diagnosis*), नैदानिक (*clinical*), न्यूनता/कमी (*deficit*), असामान्य (*abnormal*), बाधित/क्षीणता (*impaired*), विकृति/रोगविज्ञान (*pathology*), बुद्धिलब्धि/आईक्यू (*IQ*), मंदबुद्धि/मानसिक मंदता (*retardation*), अक्षमता/अपंग/विकलांग (*disability/handicap*), ऑटिज्म/आत्मकेंद्रित (*autism*), डिस्लेक्सिया/पठन विकार (*dyslexia*), एडीएचडी/अतिसक्रियता (*ADHD*), डिस्कैलकुलिया/गणना विकार (*dyscalculia*), आदि।
- **Multilingual Fallback:** If any prohibited term is detected in English or Hindi, the agent blocks the text, logs the incident, and substitutes an encouraging, strengths-based educational fallback in the appropriate language (using `DEFAULT_FALLBACK_TEXT_HI` for Devanagari text).
- **Privacy Safeguard:** To protect learner confidentiality, raw blocked text is stored exclusively in secure server-side rotating logs—the administrator dashboard displays only matched rule categories and incident counts.

### 2. Content Integrity Agent (`content_integrity_agent.py`)
- **What it does:** Continuously audits the educational catalog for anomalies: activities with zero questions, empty categories, orphaned questions, invalid difficulty levels, out-of-range age bounds (`min_age > max_age`), duplicate questions within an activity, and **translation completeness**.
- **Translation Completeness & Integrity:** Specifically inspects activities with Hindi translations to catch and report `incomplete_translation` issues:
  - Activities where the title is translated into Hindi, but questions lack Hindi translations.
  - Activities where questions have Hindi translations, but the activity title/description lacks a Hindi translation.
  - Question answer option count mismatches between English and Hindi versions (e.g. 4 English choices vs 3 Hindi choices).
  - Hindi questions where the declared correct answer is not present among the Hindi answer choices.
- **Actionable Reporting:** Reports the exact database activity ID, activity title, and precise missing components so administrators can immediately address partial or broken translations.

### 3. Platform Health Agent (`health_agent.py`)
- **What it does:** Aggregates real platform telemetry to compute an objective 0–100 overall platform health score based on session completion rates (35%), valid content coverage (35%), recommendation coverage (30%), with deductions for recent compliance incidents and content integrity issues.
- **Why it matters:** Records snapshots in the `health_snapshots` database table so administrators can monitor health trends over time via an interactive Chart.js trend line rather than viewing an isolated static number.

### 4. Adaptive Content Suggestion Agent (`content_suggestion_agent.py`)
- **What it does:** Analyzes aggregate learner demographics (`Child.age`), preferred languages (`Child.preferred_language`), category performance, gap persistence, and engagement trends (`analytics_service.compute_category_age_band_engagement_trend`) to automatically detect educational catalog gaps:
  - **Progression Gaps:** Identifies categories where learners cluster at a difficulty level with high mastery (accuracy $\ge 70\%$), but the subsequent tier lacks activities.
  - **Age Coverage Gaps:** Identifies active age bands on the platform (4–6, 6–9, 9–12, 12–14) that have fewer than 2 activities in a category.
  - **Content Imbalance:** Identifies categories with activity counts substantially lower than the platform average.
  - **Domain Expansion:** Identifies opportunities for new educational categories when active learners demonstrate high cross-domain engagement.
  - **Translation Gaps (`translation_gap`):** Queries real counted counts of Hindi-preferring learners (`Child.preferred_language == 'hi'`) in each developmental age band and detects when their cohort has fewer than 2 translated activities in a category.
- **Evidence-Dense Reasoning with Real Computed Counts:** Every number, count, and translation percentage reported is strictly computed directly from the database (e.g., *"2 registered learner(s) in age band 4-6 (Early Childhood / Pre-K) prefer Hindi, but category 'Logic' currently has only 0 translated Hindi activity(ies) out of 1 total activities (0% translated)"*). Zero estimates or placeholders are used.
- **Urgency-Based Prioritization (`priority_score`):** Computes an objective urgency score: $\text{priority\_score} = (\text{affected\_children} \times 2.0) + (\text{persistence\_count} \times 5.0) + (\text{trend\_penalty})$.
- **Strict Human-in-the-Loop Safeguard:** The agent **never auto-creates or auto-publishes content**. Suggestions are persisted in `content_suggestions` (`pending` status) with full educational evidence.
- **Admin Review Workflow:** Administrators review suggestions at `/admin/content-suggestions` and can click **"Draft with AI →"** (opening the pre-filled AI content drafting generator), **"Create Activity →"**, or **"Create Category →"** to pre-fill standard administrative forms, automatically marking the suggestion as `approved` upon publication, or **"Dismiss"** suggestions with zero action taken.

### 5. AI-Assisted Content Drafting Agent (`content_draft_agent.py`)
- **What it does:** Generates high-quality, research-grounded educational activity drafts for administrators using rich platform context:
  - **Category Style Grounding:** Analyzes existing activities in the target category as tone and question style benchmarks.
  - **Age-Band Calibration:** Inspects cross-category activities across all 5 cognitive domains for the target developmental cohort (4–6, 6–9, 9–12, 12–14) to match established vocabulary complexity and cognitive load.
  - **Curriculum Gap Targeting:** Directly incorporates data-backed gap detection reasoning from linked Content Suggestions so drafts solve genuine platform shortages.
  - **Dual-Language Generation for Translation Gaps:** When addressing a `translation_gap`, the agent generates **both English and Hindi versions together** (paired titles, descriptions, 5–6 multiple-choice questions with 4 options each, correct answers, and scaffolding hints) in a single unified draft.
  - **Bilingual Ethical Compliance Verification:** Applies both English and Hindi negative constraints in the generation prompt and validates all generated English and Hindi question prompts, options, answers, and hints through `compliance_agent.check_text()`, retrying up to 2 times and discarding non-compliant items before presenting to the administrator.
- **Strict Human-in-the-Loop Boundary:** The agent **never auto-publishes or writes directly to the database**. All generated drafts are presented in an editable review screen (`/admin/activities/ai-draft/generate`) displaying transparent grounding metadata and side-by-side editable fields for English and Hindi. Content is only committed to the database when an administrator explicitly clicks **"Approve & Publish"**, simultaneously storing both language versions in `translations_json`, while clicking **"Discard"** immediately throws the draft away.

### 6. Background Maintenance Runner (`scheduler.py`)
- **What it does:** An idempotent, fault-isolated pipeline runner (callable via CLI with `python -m flask run-agents` or triggered from the Admin Console) that systematically:
  1. Records a timestamped platform health snapshot.
  2. Refits the Scikit-learn K-Means interaction clustering model when new session data is available.
  3. Regenerates personalized activity recommendations for learners who completed new sessions.
  4. Runs content integrity and compliance validation sweeps (including translation completeness).
  5. Executes the Adaptive Content Suggestion Agent to identify curriculum and translation opportunities.
  6. Dispatches notifications to platform administrators.
  7. Consolidates cross-agent telemetry into prioritized action items via the Orchestrator Agent.
- **Why it matters:** Features concurrency locking to prevent overlapping executions and wraps each step in independent exception handling so that an issue in one task never halts the rest of the maintenance cycle.

### 7. Read-Only Action Orchestrator Agent (`orchestrator_agent.py`)
- **What it does:** Serves as a strictly read-only coordinator that pulls together the findings of all other system agents into a single, deduplicated, prioritized action list for administrators:
  - **Cross-Agent Consolidation in One Pass:** Reads all pending `content_suggestions` (including `translation_gap` opportunities), active `content_integrity_agent` catalog issues, the latest `health_agent` score and per-age-band breakdown, and 24-hour `compliance_agent` telemetry.
  - **Deduplication & Cohort Grouping:** Consolidates related findings so administrators are not overwhelmed by redundant alerts. For example, multiple progression or translation suggestions for the same category across different developmental bands become a single grouped item displaying `"affects ages 4-6, 9-12, 12-14"` with aggregated affected learner counts and persistence metrics.
  - **Objective Priority Tiering:** Assigns transparent priority tiers (`Critical`, `Important`, `Minor`) using deterministic rules based on real computed numbers:
    - *Critical (Red):* Active compliance incidents in the past 24 hours, overall platform health $< 60$, any cohort health $< 70$, or urgent curriculum gaps affecting $\ge 10$ children, persisting $\ge 3$ runs, or having a priority score $\ge 25$.
    - *Important (Amber):* Content integrity issues (empty categories, missing questions, translation completeness mismatches), moderate curriculum or translation gaps (score $\ge 10$, affected children $> 0$, or `translation_gap`).
    - *Minor (Gray):* General catalog expansion ideas with no immediate affected children or low urgency.
  - **Grounded, Plain-Language Summaries:** Every summary explains clearly *what* the issue is and *why* it matters, directly citing the underlying telemetry numbers (e.g. *"7 child(ren) (affects ages 6-9) affected by curriculum gap in Language (urgency score 19.0, persisted 2 run(s)). Addressing this prevents learning stalls."*).
  - **Zero Autonomous Mutations:** The orchestrator never creates, modifies, publishes, or deletes any activity, question, or database record. It functions exclusively as an organizational lens.
  - **Interactive Action Center:** Accessible at `/admin/agents` (and `/admin/action-center`), featuring direct deep links to existing resolution pages (e.g. `/admin/activities/ai-draft/generate`, `/admin/content-suggestions`, `/admin/activities/integrity-check`) and a session-based **"Dismiss from this view"** toggle that declutters the admin's workspace without touching or deleting any database records.

---

## 🗄️ Production Database Migration Guide

ChildInsight uses **SQLAlchemy** and **Flask-Migrate (Alembic)**, allowing seamless transitions between local SQLite and production databases.

### 1. PostgreSQL (Recommended for Production)

#### Step 1: Install Database Driver
```bash
pip install psycopg2-binary
```

#### Step 2: Provision Database
Create the target database and user in PostgreSQL:
```sql
CREATE USER childinsight_user WITH PASSWORD 'secure_production_password';
CREATE DATABASE childinsight OWNER childinsight_user;
GRANT ALL PRIVILEGES ON DATABASE childinsight TO childinsight_user;
```

#### Step 3: Update `.env` or Server Environment Variables
```env
FLASK_CONFIG=production
SECRET_KEY=generate_a_64_char_random_hex_string_using_secrets_token_hex
DATABASE_URL=postgresql://childinsight_user:secure_production_password@db-host.internal:5432/childinsight
```
*(Note: ChildInsight's `ProductionConfig` automatically normalizes legacy `postgres://` URLs provided by cloud hosts such as Render and Heroku to standard `postgresql://`).*

#### Step 4: Run Migrations on PostgreSQL
```bash
python -m flask --app run.py db upgrade
```

---

### 2. MySQL (Alternative Production Database)

#### Step 1: Install Database Driver
```bash
pip install pymysql cryptography
```

#### Step 2: Provision Database
```sql
CREATE DATABASE childinsight CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'childinsight_user'@'%' IDENTIFIED BY 'secure_production_password';
GRANT ALL PRIVILEGES ON childinsight.* TO 'childinsight_user'@'%';
FLUSH PRIVILEGES;
```

#### Step 3: Update `.env` or Server Environment Variables
```env
FLASK_CONFIG=production
SECRET_KEY=generate_a_64_char_random_hex_string_using_secrets_token_hex
DATABASE_URL=mysql+pymysql://childinsight_user:secure_production_password@db-host.internal:3306/childinsight
```

#### Step 4: Run Migrations on MySQL
```bash
python -m flask --app run.py db upgrade
```

---

## 💾 Backup & Recovery Procedures

### 1. SQLite (Local / Development)
Because SQLite databases are single files, backups can be created safely using the SQLite backup API or online backup CLI command:

```bash
# Recommended: Online atomic backup
sqlite3 database/childinsight_dev.db ".backup database/backups/childinsight_backup_$(date +%Y%m%d_%H%M%S).db"

# Direct file copy (ensure server is stopped or idle)
cp database/childinsight_dev.db database/backups/childinsight_dev.bak
```

### 2. PostgreSQL (Production)
Execute a consistent binary dump using `pg_dump`:

```bash
# Create timestamped dump
pg_dump -h $DB_HOST -U $DB_USER -d childinsight -F c -b -v -f /var/backups/childinsight_$(date +%Y%m%d_%H%M%S).dump

# Restore from dump
pg_restore -h $DB_HOST -U $DB_USER -d childinsight -v /var/backups/childinsight_YYYYMMDD_HHMMSS.dump
```

### 3. MySQL (Production)
Execute a logical backup using `mysqldump`:

```bash
# Create compressed SQL dump
mysqldump -h $DB_HOST -u $DB_USER -p --single-transaction --quick childinsight > /var/backups/childinsight_$(date +%Y%m%d_%H%M%S).sql

# Restore from SQL dump
mysql -h $DB_HOST -u $DB_USER -p childinsight < /var/backups/childinsight_YYYYMMDD_HHMMSS.sql
```

### Automated Backup Recommendation
In production, schedule daily automated backups via `cron` or cloud provider managed snapshots (e.g. AWS RDS snapshots, Render automated daily backups, DigitalOcean Managed Database backups) with offsite retention.

---

## 🔒 Production Deployment & HTTPS Setup

### 1. Security Configuration Highlights
When running with `FLASK_CONFIG=production`:
- `DEBUG = False` and `TESTING = False`.
- `SESSION_COOKIE_SECURE = True` (cookies transmitted strictly over HTTPS).
- `SESSION_COOKIE_HTTPONLY = True` (prevents JavaScript access to session tokens).
- `SESSION_COOKIE_SAMESITE = 'Lax'` (CSRF defense).
- `REMEMBER_COOKIE_SECURE = True` and `REMEMBER_COOKIE_HTTPONLY = True`.
- `ProxyFix` WSGI middleware enabled to parse upstream `X-Forwarded-For` and `X-Forwarded-Proto` headers.
- Strict startup validation requiring strong `SECRET_KEY` and explicit `DATABASE_URL`.

### 2. Deploying with Gunicorn & Nginx on Linux VM

#### Step 1: Install Gunicorn
```bash
pip install gunicorn
```

#### Step 2: Systemd Service Unit (`/etc/systemd/system/childinsight.service`)
```ini
[Unit]
Description=ChildInsight Gunicorn Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/childinsight
Environment="PATH=/var/www/childinsight/.venv/bin"
EnvironmentFile=/var/www/childinsight/.env
ExecStart=/var/www/childinsight/.venv/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 run:app

[Install]
WantedBy=multi-user.target
```

#### Step 3: Nginx Reverse Proxy Configuration (`/etc/nginx/sites-available/childinsight`)
```nginx
server {
    listen 80;
    server_name app.childinsight.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.childinsight.org;

    ssl_certificate /etc/letsencrypt/live/app.childinsight.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.childinsight.org/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /static/ {
        alias /var/www/childinsight/app/static/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Step 4: Obtain Free TLS Certificate (Certbot)
```bash
sudo certbot --nginx -d app.childinsight.org
```

### 3. Cloud PaaS Deployment (Render / Railway / Fly.io)
1. Configure environment variables in the provider dashboard:
   - `FLASK_CONFIG`: `production`
   - `SECRET_KEY`: `<generated-random-secret>`
   - `DATABASE_URL`: Linked from provider's managed PostgreSQL database.
2. Build Command:
   ```bash
   pip install -r requirements.txt && python -m flask --app run.py db upgrade
   ```
3. Start Command:
   ```bash
   gunicorn run:app
   ```
*(TLS certificates and HTTPS termination are automatically provisioned and managed by the PaaS provider).*

---

## 📜 Production Logging Standards

ChildInsight uses standard library rotating file logs (`RotatingFileHandler`):
- **Location:** `logs/childinsight.log`
- **File Rotation:** 10MB file size threshold with 5 backup archives retained.
- **Scrubbing Policy:** Passwords, plain text authentication tokens, and raw session cookie payloads are strictly prohibited from logs. Route error handlers capture only sanitized route, method, user ID, and stack trace metadata.

---

## 🏗️ Architectural Overview (Phases 1–10)

```
ChildInsight/
├── app/
│   ├── models/            # User, Child, Category, Activity, Question, Session, InteractionEvent, Recommendation, AuditLog
│   ├── routes/
│   │   ├── auth.py        # Authentication & password management
│   │   ├── parent.py      # Parent dashboard, children CRUD, reports (PDF & CSV)
│   │   ├── teacher.py     # Educator workspace, student profiles, notes, assignment
│   │   ├── child.py       # Child activity hub & interactive game player
│   │   ├── admin.py       # System stats, user management, audit logs viewer
│   │   └── api.py         # REST session tracking & health check
│   ├── services/
│   │   ├── analytics_service.py      # Category mastery, engagement index, trends
│   │   ├── recommendation_service.py # 3-layer recommendation engine (Rule, Perf, Personal)
│   │   └── audit_service.py          # Centralized audit logging for security events
│   ├── ml/
│   │   ├── features.py               # Feature vector extraction (6-dimensional domain signals)
│   │   ├── clustering.py             # K-Means clustering with dynamic semantic labels
│   │   └── model_manager.py          # Model lifecycle, training threshold, persistence
│   ├── forms/                        # Flask-WTF validation forms with CSRF protection
│   ├── utils/
│   │   ├── decorators.py             # Role validation (@role_required)
│   │   └── seed_data.py              # Full demo dataset generator with [Demo Data] badging
│   ├── templates/                    # Semantic HTML5, accessible, responsive design
│   └── static/                       # Custom CSS design system, child-friendly styling, JS
├── database/                         # Development SQLite database (childinsight_dev.db)
├── logs/                             # Production-safe rotating logs
├── migrations/                       # Alembic schema version migrations
├── tests/                            # Automated test suites (Phases 1 through 10)
├── config.py                         # Dev, test, and production configurations
└── run.py                            # CLI utilities (create-admin, seed-demo) & dev runner
```

---

## 📄 License & Compliance

ChildInsight is built for educational institutions, parents, and developmental research. Data handling complies with ethical guidelines prioritizing child privacy, transparent algorithmic accountability, and strength-based learning development.
