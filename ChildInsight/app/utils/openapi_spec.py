"""
OpenAPI 3.0.3 Specification for ChildInsight REST API.
Provides full machine-readable schema for interactive Swagger UI docs.
"""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "ChildInsight REST API",
        "version": "1.0.0",
        "description": "Interactive API documentation for ChildInsight educational platform — children profiles, activities, real-time learning sessions, analytics, recommendations, and notifications.",
        "contact": {
            "name": "ChildInsight Support",
            "url": "http://localhost:5000"
        }
    },
    "servers": [
        {
            "url": "/api",
            "description": "ChildInsight API Base URL"
        }
    ],
    "tags": [
        {"name": "System & Auth", "description": "Health check and authentication state"},
        {"name": "Children", "description": "Learner profile management and retrieval"},
        {"name": "Activities", "description": "Educational activity catalog and question details"},
        {"name": "Sessions", "description": "Interactive play session lifecycles and telemetry logs"},
        {"name": "Analytics & Progress", "description": "Computed learning performance, engagement, and mastery records"},
        {"name": "Recommendations", "description": "Tailored, explainable activity guidance"},
        {"name": "Notifications", "description": "In-dashboard learning milestones and educator assignment alerts"}
    ],
    "paths": {
        "/health": {
            "get": {
                "tags": ["System & Auth"],
                "summary": "Health check",
                "description": "Returns operational status and version of ChildInsight API.",
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "example": {
                                    "status": "healthy",
                                    "service": "ChildInsight API",
                                    "version": "1.0.0"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/auth/status": {
            "get": {
                "tags": ["System & Auth"],
                "summary": "Authentication status",
                "description": "Returns session authentication state and current user identity.",
                "responses": {
                    "200": {
                        "description": "Session status",
                        "content": {
                            "application/json": {
                                "example": {
                                    "authenticated": True,
                                    "user": {
                                        "id": 3,
                                        "name": "Jordan Smith [Demo Data]",
                                        "email": "parent@childinsight.demo",
                                        "role": "parent"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/children": {
            "get": {
                "tags": ["Children"],
                "summary": "List accessible children",
                "description": "Lists child profiles accessible to current user (parent sees their children, teacher sees assigned students, admin sees all).",
                "responses": {
                    "200": {
                        "description": "List of children",
                        "content": {
                            "application/json": {
                                "example": {
                                    "count": 3,
                                    "children": [
                                        {"id": 1, "name": "Leo [Demo Data]", "age": 6, "grade": "1st Grade", "preferred_language": "English"},
                                        {"id": 2, "name": "Mia [Demo Data]", "age": 8, "grade": "3rd Grade", "preferred_language": "English"}
                                    ]
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized — authentication required"}
                }
            }
        },
        "/children/{child_id}": {
            "get": {
                "tags": ["Children"],
                "summary": "Get child profile",
                "description": "Retrieve specific child details by ID with RBAC isolation.",
                "parameters": [
                    {
                        "name": "child_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Child ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Child profile details",
                        "content": {
                            "application/json": {
                                "example": {
                                    "id": 1,
                                    "name": "Leo [Demo Data]",
                                    "age": 6,
                                    "grade": "1st Grade",
                                    "preferred_language": "English",
                                    "parent_id": 3
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"},
                    "403": {"description": "Forbidden — user lacks permission for this child"},
                    "404": {"description": "Child not found"}
                }
            }
        },
        "/activities": {
            "get": {
                "tags": ["Activities"],
                "summary": "List active activities",
                "description": "Retrieve all active educational activities across all categories and difficulty tiers.",
                "responses": {
                    "200": {
                        "description": "List of activities",
                        "content": {
                            "application/json": {
                                "example": {
                                    "count": 83,
                                    "activities": [
                                        {"id": 1, "title": "Color Match Adventure [Demo Data]", "category": "Visual Learning", "category_id": 1, "difficulty": "Beginner", "estimated_duration": 5}
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        "/activities/{activity_id}": {
            "get": {
                "tags": ["Activities"],
                "summary": "Get activity details",
                "description": "Get full activity details including description, category, and ordered questions with choice options.",
                "parameters": [
                    {
                        "name": "activity_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Activity ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Activity details and questions",
                        "content": {
                            "application/json": {
                                "example": {
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
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    "404": {"description": "Activity not found"}
                }
            }
        },
        "/sessions": {
            "post": {
                "tags": ["Sessions"],
                "summary": "Start a new session",
                "description": "Initiate an activity session for an authorized child. Supersedes previous unclosed sessions.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["child_id", "activity_id"],
                                "properties": {
                                    "child_id": {"type": "integer", "example": 1},
                                    "activity_id": {"type": "integer", "example": 1}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Session created and started",
                        "content": {
                            "application/json": {
                                "example": {
                                    "message": "Session started",
                                    "session": {
                                        "id": 19,
                                        "child_id": 1,
                                        "activity_id": 1,
                                        "activity_title": "Color Match Adventure [Demo Data]",
                                        "category_name": "Visual Learning",
                                        "status": "in_progress",
                                        "start_time": "2026-09-12T06:15:00Z",
                                        "duration_seconds": 0,
                                        "attempts": 0,
                                        "correct_answers": 0,
                                        "accuracy": 0.0
                                    }
                                }
                            }
                        }
                    },
                    "400": {"description": "Validation error — missing or invalid fields"},
                    "401": {"description": "Unauthorized"},
                    "403": {"description": "Forbidden"},
                    "404": {"description": "Child or Activity not found"}
                }
            }
        },
        "/sessions/{session_id}": {
            "get": {
                "tags": ["Sessions"],
                "summary": "Get session and event telemetry",
                "description": "Retrieve session summary and chronological interaction events.",
                "parameters": [
                    {
                        "name": "session_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Session ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Session details and event stream",
                        "content": {
                            "application/json": {
                                "example": {
                                    "session": {
                                        "id": 1,
                                        "child_id": 1,
                                        "activity_id": 1,
                                        "status": "completed",
                                        "duration_seconds": 300,
                                        "accuracy": 100.0,
                                        "events": [
                                            {
                                                "id": 1,
                                                "event_type": "started",
                                                "timestamp": "2026-09-08T06:00:01Z"
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"},
                    "403": {"description": "Forbidden"},
                    "404": {"description": "Session not found"}
                }
            }
        },
        "/analytics/{child_id}": {
            "get": {
                "tags": ["Analytics & Progress"],
                "summary": "Get child analytics snapshot",
                "description": "Returns calculated learning metrics including overall accuracy, completion rate, consistency score, engagement index, and category breakdowns.",
                "parameters": [
                    {
                        "name": "child_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Child ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Analytics snapshot",
                        "content": {
                            "application/json": {
                                "example": {
                                    "analytics": {
                                        "child_id": 1,
                                        "total_sessions": 6,
                                        "completed_sessions": 6,
                                        "overall_accuracy": 95.0,
                                        "overall_completion_rate": 100.0,
                                        "consistency_score": 96.2,
                                        "engagement_index": 88.5,
                                        "categories": {
                                            "visual": {"sessions": 2, "accuracy": 95.0, "completion_rate": 100.0, "avg_duration": 280.0}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"},
                    "403": {"description": "Forbidden"},
                    "404": {"description": "Child not found"}
                }
            }
        },
        "/progress/{child_id}": {
            "get": {
                "tags": ["Analytics & Progress"],
                "summary": "Get category progress records",
                "description": "Fetch persisted progress records per category. Optional query parameter `refresh=true` re-calculates from raw sessions.",
                "parameters": [
                    {
                        "name": "child_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Child ID"
                    },
                    {
                        "name": "refresh",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "boolean"},
                        "description": "Set to true to force recalculation"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Progress records per category",
                        "content": {
                            "application/json": {
                                "example": {
                                    "child_id": 1,
                                    "count": 5,
                                    "records": [
                                        {
                                            "id": 1,
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
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"},
                    "403": {"description": "Forbidden"},
                    "404": {"description": "Child not found"}
                }
            },
            "post": {
                "tags": ["Analytics & Progress"],
                "summary": "Recalculate category progress records",
                "description": "Forces recomputation of progress records for all categories from historical session data.",
                "parameters": [
                    {
                        "name": "child_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Child ID"
                    }
                ],
                "responses": {
                    "200": {"description": "Updated progress records list"}
                }
            }
        },
        "/recommendations/{child_id}": {
            "get": {
                "tags": ["Recommendations"],
                "summary": "Get activity recommendations",
                "description": "Returns top explainable, priority-ranked activity recommendations using the 3-layer engine.",
                "parameters": [
                    {
                        "name": "child_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Child ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Ranked activity recommendations",
                        "content": {
                            "application/json": {
                                "example": {
                                    "child_id": 1,
                                    "count": 2,
                                    "recommendations": [
                                        {
                                            "activity_id": 3,
                                            "activity_title": "Rainbow Sorting Quest [Demo Data]",
                                            "category_name": "Visual Learning",
                                            "difficulty": "Easy",
                                            "recommendation_type": "reinforce",
                                            "reason": "Strong accuracy (95%) with good completion in Visual Learning. Continuing with Easy activity to build confidence. Let's try Rainbow Sorting Quest [Demo Data] in Visual Learning.",
                                            "priority": 1
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"},
                    "403": {"description": "Forbidden"},
                    "404": {"description": "Child not found"}
                }
            }
        },
        "/notifications": {
            "get": {
                "tags": ["Notifications"],
                "summary": "List notifications",
                "description": "Retrieve recent notifications and unread count for the currently logged-in user.",
                "parameters": [
                    {
                        "name": "unread_only",
                        "in": "query",
                        "schema": {"type": "boolean", "default": False},
                        "description": "Filter to unread notifications only"
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 20, "maximum": 50},
                        "description": "Max notifications to return"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "User notifications and unread badge count",
                        "content": {
                            "application/json": {
                                "example": {
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
                                            "is_read": False,
                                            "created_at": "2026-09-12T05:20:00Z"
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"}
                }
            }
        },
        "/notifications/{notification_id}/read": {
            "post": {
                "tags": ["Notifications"],
                "summary": "Mark notification as read",
                "description": "Mark a specific notification as read by ID.",
                "parameters": [
                    {
                        "name": "notification_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Notification ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Notification marked as read",
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": True,
                                    "notification_id": 1,
                                    "unread_count": 0
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"},
                    "404": {"description": "Notification not found or unauthorized"}
                }
            }
        },
        "/notifications/mark-all-read": {
            "post": {
                "tags": ["Notifications"],
                "summary": "Mark all notifications read",
                "description": "Mark all pending notifications as read for current user.",
                "responses": {
                    "200": {
                        "description": "All notifications marked as read",
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": True,
                                    "marked_count": 3,
                                    "unread_count": 0
                                }
                            }
                        }
                    },
                    "401": {"description": "Unauthorized"}
                }
            }
        }
    }
}
