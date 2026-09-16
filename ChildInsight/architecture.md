# ChildInsight — architecture.md

## 1. High-Level Architecture

```
Presentation Layer      → HTML / CSS / JS / Chart.js
Application Layer       → Flask routes, auth, role management, REST API
Intelligence Layer      → analytics, engagement scoring, recommendation engine, ML (K-Means)
Data Layer              → SQLAlchemy ORM over SQLite (dev) / MySQL (prod)
Security & Privacy      → access control, validation, secure data handling, audit log
```

Data flow (the core technical story of the project):

```
Child Activity → Event Collection → Database → Data Validation →
Pandas Processing → Feature Engineering → Analytics →
Rule Engine + ML (K-Means) → Explainable Recommendation → Dashboard
```

## 2. Folder & File Structure

```
ChildInsight/
├── run.py
├── config.py
├── requirements.txt
├── .env
├── README.md
├── PRD.md
├── architecture.md
├── rules.md
├── phases.md
├── design.md
├── memory.md
│
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── user.py
│   │   ├── child.py
│   │   ├── activity.py
│   │   ├── session.py
│   │   ├── recommendation.py
│   │   └── progress.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── parent.py
│   │   ├── teacher.py
│   │   ├── child.py
│   │   ├── admin.py
│   │   └── api.py
│   ├── services/
│   │   ├── analytics_service.py
│   │   ├── engagement_service.py
│   │   ├── recommendation_service.py
│   │   ├── profile_service.py
│   │   └── report_service.py
│   ├── ml/
│   │   ├── features.py
│   │   ├── clustering.py
│   │   └── model_manager.py
│   ├── utils/
│   ├── templates/
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
│
├── migrations/
├── tests/
└── database/
```

## 3. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend framework | Flask | Lightweight, modular, integrates cleanly with SQLAlchemy/Pandas/Scikit-learn |
| ORM / DB | SQLAlchemy + SQLite (dev) → MySQL/PostgreSQL (prod) | Easy local dev, clean migration path |
| Data processing | Pandas, NumPy | Session-data cleaning, aggregation, feature engineering |
| ML | Scikit-learn (K-Means) | Pattern grouping of activity interaction features |
| Frontend | HTML, CSS, vanilla JS (+ Chart.js) | No build step needed, keeps the project simple to run/demo |
| PDF/CSV export | reportlab or WeasyPrint / pandas.to_csv | Report generation |
| Auth | Flask-Login + Werkzeug password hashing | Session-based auth, industry standard for Flask |
| Migrations | Flask-Migrate (Alembic) | Versioned schema changes |

## 4. Database Architecture (entity relationships)

```
users
  ├── children (parent_id FK)
  └── teacher_assignments

children
  ├── activity_sessions
  │     ├── interaction_events
  │     └── session_answers
  ├── learning_profiles
  ├── recommendations
  └── progress_records

activities
  ├── activity_questions
  └── categories
```

Core tables (fields), see `rules.md` for naming conventions:
`users, children, activities, activity_questions, activity_sessions,
interaction_events, recommendations, progress_records, learning_profiles`.

## 5. API Surface (clean separation so a future mobile app can reuse it)

```
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/children
GET    /api/children/<id>
GET    /api/activities
GET    /api/activities/<id>
POST   /api/sessions
GET    /api/sessions/<id>
GET    /api/analytics/<child_id>
GET    /api/recommendations/<child_id>
GET    /api/progress/<child_id>
```
