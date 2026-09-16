# ChildInsight REST API Documentation

The ChildInsight REST API provides a programmatic interface for interacting with children profiles, educational activities, live learning sessions, telemetry events, analytics snapshots, tailored recommendations, and user notifications.

---

## 📌 Architecture & Design Principles

1. **Clean Separation**: Built under the `/api/` prefix to allow future mobile apps, browser clients, or third-party integrations to seamlessly reuse backend services without relying on HTML templates.
2. **CSRF Exemption**: All routes under `/api/` are exempt from CSRF validation (`csrf.exempt(api_bp)`), simplifying programmatic HTTP requests.
3. **Session Authentication**: State is authenticated via standard Flask session cookies established at login. Unauthorized requests return `401 Unauthorized`.
4. **Role-Based Access Control (RBAC)**:
   - **`public`**: Accessible without authentication (e.g. `/api/health`, `/api/auth/status`, `/api/activities`).
   - **`parent`**: Can view and manage only their own children (`child.parent_id == current_user.id`).
   - **`teacher`**: Can access data only for students assigned to them via `TeacherAssignment`.
   - **`admin`**: Full platform-wide visibility across all children, sessions, and analytics.
5. **JSON Payloads**: All responses and JSON request bodies strictly use `application/json`.
6. **Zero Diagnostic Language**: In accordance with PRD §4 ethical mandates, API responses never expose medical, clinical, or diagnostic labels.

---

## 🗺️ Quick Reference Table

| Method | Endpoint | Auth Required | Permitted Roles | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | No | Public | Service health & version status |
| `GET` | `/api/auth/status` | No | Public | Current user session state |
| `GET` | `/api/children` | Yes | Parent, Teacher, Admin | List accessible children profiles |
| `GET` | `/api/children/{id}` | Yes | Child Parent, Assigned Teacher, Admin | Get single child profile |
| `GET` | `/api/activities` | No | Public | List all active educational activities |
| `GET` | `/api/activities/{id}` | No | Public | Get activity details with questions |
| `POST` | `/api/sessions` | Yes | Child Parent, Assigned Teacher, Admin | Start a new activity session |
| `GET` | `/api/sessions/{id}` | Yes | Child Parent, Assigned Teacher, Admin | Retrieve session details & event stream |
| `GET` | `/api/analytics/{child_id}` | Yes | Child Parent, Assigned Teacher, Admin | Calculated analytics snapshot |
| `GET` | `/api/progress/{child_id}` | Yes | Child Parent, Assigned Teacher, Admin | Fetch category progress records |
| `POST` | `/api/progress/{child_id}` | Yes | Child Parent, Assigned Teacher, Admin | Force recalculate progress records |
| `GET` | `/api/recommendations/{child_id}` | Yes | Child Parent, Assigned Teacher, Admin | Explainable activity recommendations |
| `GET` | `/api/notifications` | Yes | Authenticated Users | User notifications & unread count |
| `POST` | `/api/notifications/{id}/read` | Yes | Notification Recipient | Mark notification as read |
| `POST` | `/api/notifications/mark-all-read`| Yes | Authenticated Users | Mark all user notifications as read |
| `GET` | `/api/docs` | No | Public | Interactive Swagger UI API Explorer |
| `GET` | `/api/openapi.json` | No | Public | OpenAPI 3.0.3 specification |

---

## 📖 Endpoint Details

### 1. Health Check
Checks service operational status and version.

- **Method**: `GET`
- **Path**: `/api/health`
- **Auth**: None (Public)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "service": "ChildInsight API",
    "status": "healthy",
    "version": "1.0.0"
  }
  ```

---

### 2. Authentication Status
Inspects whether the calling client possesses an active authenticated session.

- **Method**: `GET`
- **Path**: `/api/auth/status`
- **Auth**: None (Public)
- **Request Body**: None
- **Response `200 OK` (Authenticated)**:
  ```json
  {
    "authenticated": true,
    "user": {
      "id": 3,
      "name": "Jordan Smith [Demo Data]",
      "email": "parent@childinsight.demo",
      "role": "parent"
    }
  }
  ```
- **Response `200 OK` (Unauthenticated)**:
  ```json
  {
    "authenticated": false,
    "user": null
  }
  ```

---

### 3. List Children
Lists all child profiles accessible to the currently authenticated user.

- **Method**: `GET`
- **Path**: `/api/children`
- **Auth**: Required (`parent`, `teacher`, `admin`)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "count": 3,
    "children": [
      {
        "id": 1,
        "name": "Leo [Demo Data]",
        "age": 6,
        "grade": "1st Grade",
        "preferred_language": "English"
      },
      {
        "id": 2,
        "name": "Mia [Demo Data]",
        "age": 8,
        "grade": "3rd Grade",
        "preferred_language": "English"
      },
      {
        "id": 3,
        "name": "Noah [Demo Data]",
        "age": 7,
        "grade": "2nd Grade",
        "preferred_language": "English"
      }
    ]
  }
  ```
- **Errors**:
  - `401 Unauthorized`:
    ```json
    { "error": "Unauthorized" }
    ```

---

### 4. Get Child Details
Retrieves details for a specific child profile by ID.

- **Method**: `GET`
- **Path**: `/api/children/{child_id}`
- **Auth**: Required (Parent of child, Assigned Teacher, Admin)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "id": 1,
    "name": "Leo [Demo Data]",
    "age": 6,
    "grade": "1st Grade",
    "preferred_language": "English",
    "parent_id": 3
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Client is not logged in (`{"error": "Unauthorized"}`).
  - `403 Forbidden`: User is logged in but lacks authorization to view this child (`{"error": "Forbidden"}`).
  - `404 Not Found`: Child ID does not exist (`{"error": "Child not found"}`).

---

### 5. List Activities
Retrieves all active educational activities.

- **Method**: `GET`
- **Path**: `/api/activities`
- **Auth**: None (Public)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "count": 83,
    "activities": [
      {
        "id": 1,
        "title": "Color Match Adventure [Demo Data]",
        "category": "Visual Learning",
        "category_id": 1,
        "difficulty": "Beginner",
        "estimated_duration": 5
      },
      {
        "id": 5,
        "title": "Pattern Spotter [Demo Data]",
        "category": "Visual Learning",
        "category_id": 1,
        "difficulty": "Easy",
        "estimated_duration": 6
      }
    ]
  }
  ```

---

### 6. Get Activity Details
Retrieves full activity details, including ordered questions and choice options.

- **Method**: `GET`
- **Path**: `/api/activities/{activity_id}`
- **Auth**: None (Public)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "id": 1,
    "title": "Color Match Adventure [Demo Data]",
    "description": "Help the painter mix magical colors and spot shapes in nature!",
    "category": "Visual Learning",
    "difficulty": "Beginner",
    "estimated_duration": 5,
    "questions": [
      {
        "id": 1,
        "question_text": "What magical new color appears when you mix sunny yellow and bright red together?",
        "options": ["Orange", "Blue", "Green", "Purple"],
        "order_num": 1
      },
      {
        "id": 2,
        "question_text": "Which friendly shape has 3 straight sides and 3 pointy corners?",
        "options": ["Triangle", "Square", "Circle", "Rectangle"],
        "order_num": 2
      }
    ]
  }
  ```
- **Errors**:
  - `404 Not Found`:
    ```json
    { "error": "Activity not found" }
    ```

---

### 7. Start Activity Session
Creates and starts a new learning activity session for a child. Automatically supersedes any previous unclosed session left in progress.

- **Method**: `POST`
- **Path**: `/api/sessions`
- **Auth**: Required (Parent of child, Assigned Teacher, Admin)
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "child_id": 1,
    "activity_id": 1
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "message": "Session started",
    "session": {
      "id": 19,
      "child_id": 1,
      "activity_id": 1,
      "activity_title": "Color Match Adventure [Demo Data]",
      "category_name": "Visual Learning",
      "status": "in_progress",
      "start_time": "2026-09-12T06:15:00.123456Z",
      "end_time": null,
      "duration_seconds": 0,
      "attempts": 0,
      "correct_answers": 0,
      "accuracy": 0.0,
      "created_at": "2026-09-12T06:15:00.123456Z"
    }
  }
  ```
- **Errors**:
  - `400 Bad Request`: Missing fields or non-positive integers (`{"error": "child_id and activity_id are required"}` or `{"error": "child_id and activity_id must be positive integers"}`).
  - `401 Unauthorized`: Not logged in (`{"error": "Unauthorized"}`).
  - `403 Forbidden`: Unauthorized to create sessions for this child (`{"error": "Forbidden"}`).
  - `404 Not Found`: Target child or activity does not exist (`{"error": "Child not found"}` or `{"error": "Activity not found"}`).

---

### 8. Get Session Details & Events
Retrieves full metadata for a session, including all chronologically recorded interaction events.

- **Method**: `GET`
- **Path**: `/api/sessions/{session_id}`
- **Auth**: Required (Parent of child, Assigned Teacher, Admin)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "session": {
      "id": 1,
      "child_id": 1,
      "activity_id": 1,
      "activity_title": "Color Match Adventure [Demo Data]",
      "category_name": "Visual Learning",
      "status": "completed",
      "start_time": "2026-09-08T06:00:00Z",
      "end_time": "2026-09-08T06:05:00Z",
      "duration_seconds": 300,
      "attempts": 3,
      "correct_answers": 3,
      "accuracy": 100.0,
      "created_at": "2026-09-08T06:00:00Z",
      "events": [
        {
          "id": 1,
          "session_id": 1,
          "child_id": 1,
          "question_id": 1,
          "event_type": "started",
          "payload": {},
          "timestamp": "2026-09-08T06:00:01Z"
        },
        {
          "id": 2,
          "session_id": 1,
          "child_id": 1,
          "question_id": 1,
          "event_type": "answer_submit",
          "payload": {
            "selected": "Orange",
            "is_correct": true,
            "time_taken_seconds": 12.4
          },
          "timestamp": "2026-09-08T06:00:15Z"
        }
      ]
    }
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Client is not authenticated.
  - `403 Forbidden`: Client cannot access this child's session.
  - `404 Not Found`: Session ID does not exist (`{"error": "Session not found"}`).

---

### 9. Get Child Analytics Snapshot
Returns computed developmental analytics metrics: overall accuracy, completion rate, consistency score, engagement index, and domain-by-domain breakdowns.

- **Method**: `GET`
- **Path**: `/api/analytics/{child_id}`
- **Auth**: Required (Parent of child, Assigned Teacher, Admin)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "analytics": {
      "child_id": 1,
      "total_sessions": 6,
      "completed_sessions": 6,
      "overall_accuracy": 95.0,
      "overall_completion_rate": 100.0,
      "consistency_score": 96.2,
      "engagement_index": 88.5,
      "categories": {
        "visual": {
          "sessions": 2,
          "accuracy": 95.0,
          "completion_rate": 100.0,
          "avg_duration": 280.0
        },
        "memory": {
          "sessions": 2,
          "accuracy": 92.5,
          "completion_rate": 100.0,
          "avg_duration": 290.0
        }
      }
    }
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Not authenticated.
  - `403 Forbidden`: Unauthorized to view analytics for this child.
  - `404 Not Found`: Child does not exist (`{"error": "Child not found"}`).

---

### 10. Get or Update Category Progress
Fetches persisted `ProgressRecord` objects per category. Passing `?refresh=true` or issuing a `POST` forces re-computation of progress from raw session logs.

- **Method**: `GET` or `POST`
- **Path**: `/api/progress/{child_id}`
- **Query Parameters**:
  - `refresh`: Optional boolean (`true` or `false`). When `true`, recalculates progress from sessions.
- **Auth**: Required (Parent of child, Assigned Teacher, Admin)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "child_id": 1,
    "count": 5,
    "records": [
      {
        "id": 1,
        "child_id": 1,
        "category_id": 1,
        "category_name": "Visual Learning",
        "category_slug": "visual",
        "accuracy": 95.0,
        "completion_rate": 100.0,
        "engagement_score": 88.5,
        "performance_score": 93.4,
        "recorded_at": "2026-09-12T06:00:00Z"
      }
    ]
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Client is not authenticated.
  - `403 Forbidden`: Client cannot access this child's progress.
  - `404 Not Found`: Child ID not found (`{"error": "Child not found"}`).

---

### 11. Get Recommendations
Returns explainable, prioritized activity recommendations generated by the 3-layer recommendation engine (Rule-Based, Performance-Based, and Engagement-Weighted).

- **Method**: `GET`
- **Path**: `/api/recommendations/{child_id}`
- **Auth**: Required (Parent of child, Assigned Teacher, Admin)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "child_id": 1,
    "count": 3,
    "recommendations": [
      {
        "child_id": 1,
        "activity_id": 3,
        "activity_title": "Rainbow Sorting Quest [Demo Data]",
        "category_name": "Visual Learning",
        "category_slug": "visual",
        "difficulty": "Easy",
        "recommendation_type": "reinforce",
        "reason": "Strong accuracy (95%) with good completion in Visual Learning. Continuing with Easy activity to build confidence. Let's try Rainbow Sorting Quest [Demo Data] in Visual Learning.",
        "priority": 1
      },
      {
        "child_id": 1,
        "activity_id": 7,
        "activity_title": "Animal Hide & Seek [Demo Data]",
        "category_name": "Memory",
        "category_slug": "memory",
        "difficulty": "Easy",
        "recommendation_type": "reinforce",
        "reason": "Strong accuracy (92%) with good completion in Memory. Continuing with Easy activity to build confidence. Let's try Animal Hide & Seek [Demo Data] in Memory.",
        "priority": 2
      }
    ]
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Client not authenticated.
  - `403 Forbidden`: Unauthorized to view recommendations for this child.
  - `404 Not Found`: Child ID not found (`{"error": "Child not found"}`).

---

### 12. List User Notifications
Retrieves recent in-dashboard notifications and unread badge count for the logged-in user.

- **Method**: `GET`
- **Path**: `/api/notifications`
- **Auth**: Required (`@login_required`)
- **Query Parameters**:
  - `unread_only`: Optional boolean string (`true` or `false`, default: `false`).
  - `limit`: Optional integer (default: 20, maximum: 50).
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "unread_count": 1,
    "notifications": [
      {
        "id": 1,
        "user_id": 3,
        "child_id": 1,
        "child_name": "Leo [Demo Data]",
        "notification_type": "activity_completion",
        "message": "Leo completed 5 activities today. Strong performance: Visual Learning, Memory.",
        "link": "/parent/children/1",
        "is_read": false,
        "created_at": "2026-09-12T05:20:00Z"
      }
    ]
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Session cookie missing or expired.

---

### 13. Mark Notification as Read
Marks a single notification as read by ID.

- **Method**: `POST`
- **Path**: `/api/notifications/{notification_id}/read`
- **Auth**: Required (`@login_required`)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "notification_id": 1,
    "unread_count": 0
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Session cookie missing.
  - `404 Not Found`: Notification does not exist or belongs to another user (`{"error": "Notification not found or unauthorized"}`).

---

### 14. Mark All Notifications Read
Marks all pending unread notifications as read for the current user.

- **Method**: `POST`
- **Path**: `/api/notifications/mark-all-read`
- **Auth**: Required (`@login_required`)
- **Request Body**: None
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "marked_count": 3,
    "unread_count": 0
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Session cookie missing.

---

### 15. OpenAPI Specification & Interactive Explorer
ChildInsight bundles an interactive Swagger UI API Explorer requiring zero build tools.

- **Interactive Explorer**: `GET /api/docs`
  - Renders full interactive Swagger UI loaded via CDN.
  - Enables direct browser-based endpoint inspection, request execution, and response viewing without third-party tools like Postman.
- **OpenAPI 3.0.3 Spec**: `GET /api/openapi.json`
  - Returns complete machine-readable OpenAPI specification JSON.
