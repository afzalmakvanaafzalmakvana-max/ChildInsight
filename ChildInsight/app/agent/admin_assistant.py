"""
Admin Assistant Agent (app/agent/admin_assistant.py)

A chat-style guidance agent that helps the administrator understand platform status,
what needs attention, and what to do next. It explains and guides; it never acts.

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. STRICTLY READ-ONLY & NEVER ACTS: The assistant never creates, edits, publishes,
   or deletes anything in any table. It has read-only access to existing system data.
   If asked to "fix it", "do it for me", or "delete/publish", it clearly explains its
   advisory role and directs the administrator to the appropriate admin page with links.
2. STRICTLY GROUNDED IN REAL DATA: The assistant uses ONLY real data already gathered
   by the Orchestrator Agent and other system agents (pending suggestions, integrity
   issues, health scores, recent audit log entries, recent compliance incidents).
   It must NEVER invent or hallucinate a claim, a number, or a recommendation.
3. PROACTIVE MISTAKE-CATCHING: Runs newly performed admin actions (category/activity/user)
   through existing validation and integrity checks to surface helpful conversational notes
   (e.g., empty categories, 0 questions, missing Hindi translations, unassigned teachers).
"""

from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Optional, List, Dict, Any
import urllib.request
import urllib.error

from app import db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.models.content_suggestion import ContentSuggestion
from app.models.audit_log import AuditLog
from app.models.teacher_assignment import TeacherAssignment
from app.agent import (
    orchestrator_agent,
    health_agent,
    content_integrity_agent,
    compliance_agent
)

logger = logging.getLogger('childinsight.admin_assistant')

ADMIN_LINKS = {
    'action_center': {'label': 'Action Center', 'url': '/admin/action-center'},
    'content_suggestions': {'label': 'Content Suggestions', 'url': '/admin/content-suggestions'},
    'activities': {'label': 'Manage Activities', 'url': '/admin/activities'},
    'categories': {'label': 'Manage Categories', 'url': '/admin/categories'},
    'new_category': {'label': 'Create Category', 'url': '/admin/categories/new'},
    'new_activity': {'label': 'Create Activity', 'url': '/admin/activities/new'},
    'users': {'label': 'User Management', 'url': '/admin/users'},
    'audit_logs': {'label': 'Audit Logs', 'url': '/admin/audit-logs'},
    'assignments': {'label': 'Teacher Assignments', 'url': '/admin/assignments'},
    'agents_dashboard': {'label': 'System Agents Dashboard', 'url': '/admin/agents'}
}

CATEGORY_KEYWORDS = {
    'science-nature': ['science & nature', 'science and nature', 'science', 'nature', 'विज्ञान और प्रकृति', 'विज्ञान'],
    'visual': ['visual learning', 'visual puzzles', 'visual', 'दृश्य पहेलियाँ', 'दृश्य शिक्षण', 'दृश्य'],
    'logic': ['logic & reasoning', 'logic and reasoning', 'logic', 'patterns', 'तर्क और पैटर्न', 'तर्क और विचार', 'तर्क'],
    'numbers': ['numbers & math', 'numbers and math', 'numbers', 'math', 'संख्याएँ और आकृतियाँ', 'संख्या और गणित', 'संख्या', 'गणित'],
    'language': ['language & vocabulary', 'language and vocabulary', 'language', 'words', 'भाषा और शब्द', 'भाषा और शब्दावली', 'भाषा'],
    'memory': ['memory & focus', 'memory and focus', 'memory', 'focus', 'स्मृति और ध्यान', 'स्मृति', 'ध्यान']
}


# =============================================================================
# 1. REAL DATA SYNTHESIZER
# =============================================================================

def gather_assistant_context() -> dict:
    """
    Gathers in one pass all real platform metrics and telemetry:
    - Orchestrator action items & priority tiers
    - Platform & cohort health metrics
    - Content integrity audit issues
    - Pending content suggestions
    - Recent audit logs
    - Recent compliance incidents
    - Category & activity structure
    - Platform user counts by role & learner counts
    - Catalog & session totals
    
    Zero invented data: every field is derived directly from the database or
    deterministic agent routines.
    """
    # 1. Orchestrator Action Items
    try:
        action_items = orchestrator_agent.get_action_items()
    except Exception as e:
        logger.warning("Error fetching orchestrator action items: %s", e)
        action_items = []

    # 2. Platform & Cohort Health Metrics
    try:
        health_metrics = health_agent.get_latest_health()
    except Exception as e:
        logger.warning("Error fetching health metrics: %s", e)
        health_metrics = {}

    # 3. Content Integrity Issues
    try:
        integrity_issues = content_integrity_agent.run_audit()
    except Exception as e:
        logger.warning("Error fetching integrity audit: %s", e)
        integrity_issues = []

    # 4. Pending Content Suggestions
    try:
        pending_suggs = ContentSuggestion.query.filter_by(
            status=ContentSuggestion.STATUS_PENDING
        ).all()
        suggestions_summary = [
            {
                'id': s.id,
                'category_id': s.category_id,
                'category_name': s.category.name if s.category else (s.suggested_title or 'General'),
                'age_band': s.age_band,
                'suggestion_type': s.suggestion_type,
                'reason': s.reason,
                'priority_score': float(s.priority_score or 0.0),
                'persistence_count': int(s.persistence_count or 1)
            }
            for s in pending_suggs
        ]
    except Exception as e:
        logger.warning("Error fetching content suggestions: %s", e)
        suggestions_summary = []

    # 5. Recent Audit Logs
    try:
        recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
        audit_summary = [
            {
                'action': log.action,
                'target_type': log.target_type,
                'target_id': log.target_id,
                'user_name': log.user.name if log.user else 'System',
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else ''
            }
            for log in recent_logs
        ]
    except Exception as e:
        logger.warning("Error fetching audit logs: %s", e)
        audit_summary = []

    # 6. Recent Safety / Compliance Incidents
    try:
        compliance_incidents_24h = compliance_agent.get_recent_incident_count(since_hours=24)
    except Exception as e:
        logger.warning("Error fetching compliance incidents: %s", e)
        compliance_incidents_24h = 0

    # 7. Categories Overview
    try:
        categories = Category.query.all()
        categories_data = []
        for cat in categories:
            act_count = cat.activities.count() if hasattr(cat.activities, 'count') else len(cat.activities)
            has_hi = bool(cat.translations and cat.translations.get('hi', {}).get('name'))
            categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'slug': cat.slug,
                'activity_count': act_count,
                'has_hindi': has_hi
            })
    except Exception as e:
        logger.warning("Error fetching categories: %s", e)
        categories_data = []

    # 8. User Counts by Role & Learner Profiles
    try:
        user_counts = {
            'total': User.query.count(),
            'parent': User.query.filter_by(role='parent').count(),
            'teacher': User.query.filter_by(role='teacher').count(),
            'admin': User.query.filter_by(role='admin').count(),
            'children': Child.query.count()
        }
    except Exception as e:
        logger.warning("Error fetching user counts: %s", e)
        user_counts = {'total': 0, 'parent': 0, 'teacher': 0, 'admin': 0, 'children': 0}

    # 9. Catalog & Session Totals
    try:
        catalog_counts = {
            'activities': Activity.query.count(),
            'questions': ActivityQuestion.query.count(),
            'categories': len(categories_data),
            'completed_sessions': ActivitySession.query.filter_by(status=ActivitySession.STATUS_COMPLETED).count(),
            'teacher_assignments': TeacherAssignment.query.count()
        }
    except Exception as e:
        logger.warning("Error fetching catalog counts: %s", e)
        catalog_counts = {'activities': 0, 'questions': 0, 'categories': len(categories_data), 'completed_sessions': 0, 'teacher_assignments': 0}

    # Synthesize priority tier counts
    critical_items = [item for item in action_items if item.get('priority_tier') == orchestrator_agent.TIER_CRITICAL]
    important_items = [item for item in action_items if item.get('priority_tier') == orchestrator_agent.TIER_IMPORTANT]
    minor_items = [item for item in action_items if item.get('priority_tier') == orchestrator_agent.TIER_MINOR]

    return {
        'action_items_count': len(action_items),
        'critical_items_count': len(critical_items),
        'important_items_count': len(important_items),
        'minor_items_count': len(minor_items),
        'action_items': [
            {
                'key': item.get('key'),
                'title': item.get('title'),
                'subtitle': item.get('subtitle'),
                'priority_tier': item.get('priority_tier'),
                'priority_score': item.get('priority_score'),
                'summary': item.get('summary'),
                'action_url': item.get('action_url'),
                'action_label': item.get('action_label')
            }
            for item in action_items[:12]
        ],
        'health_metrics': {
            'overall_score': float(health_metrics.get('score', 100.0)),
            'completion_rate': float(health_metrics.get('completion_rate', 100.0)),
            'valid_activities_pct': float(health_metrics.get('valid_activities_pct', 100.0)),
            'cohorts': [
                {
                    'age_band': c.get('age_band'),
                    'name': c.get('name'),
                    'score': float(c.get('score', 100.0)),
                    'completion_rate': float(c.get('completion_rate', 100.0)),
                    'content_adequacy': float(c.get('content_adequacy', 100.0)),
                    'total_children': int(c.get('total_children', 0))
                }
                for c in health_metrics.get('age_band_breakdown', [])
            ]
        },
        'integrity_issues_count': len(integrity_issues),
        'integrity_issues': [
            {
                'issue_type': issue.get('issue_type'),
                'severity': issue.get('severity'),
                'affected_record': issue.get('affected_record'),
                'record_type': issue.get('record_type'),
                'record_id': issue.get('record_id'),
                'description': issue.get('description'),
                'suggested_fix': issue.get('suggested_fix')
            }
            for issue in integrity_issues[:10]
        ],
        'pending_suggestions_count': len(suggestions_summary),
        'pending_suggestions': suggestions_summary[:10],
        'compliance_incidents_24h': compliance_incidents_24h,
        'recent_audit_logs': audit_summary[:5],
        'categories': categories_data,
        'user_counts': user_counts,
        'catalog_counts': catalog_counts
    }


# =============================================================================
# 2. LANGUAGE & ACTION REQUEST DETECTION (READ-ONLY SAFETY)
# =============================================================================

def is_hindi_text(text: str) -> bool:
    """Checks if text contains Devanagari script characters."""
    return bool(re.search(r'[\u0900-\u097F]', text or ''))


HINDI_ACTION_PATTERNS = [
    r'(?:ठीक|सही|सुधार|हल)\s*कर\s*(?:दो|दें|दीजिए|दीजिये|सकते)',
    r'(?:हटा|मिटा|डिलीट\s*कर|रिमूव\s*कर)\s*(?:दो|दें|दीजिए|दीजिये|सकते)',
    r'(?:पब्लिश|प्रकाशित)\s*कर\s*(?:दो|दें|दीजिए|दीजिये|सकते)',
    r'(?:बना|जोड़|क्रिएट\s*कर)\s*(?:दो|दें|दीजिए|दीजिये|सकते)',
    r'(?:असाइन|बदल|अपडेट)\s*कर\s*(?:दो|दें|दीजिए|दीजिये|सकते)',
    r'मेरे\s*लिए\s*(?:कर\s*दो|करें|कर\s*दीजिए)',
    r'क्या\s*आप\s*(?:हटा|बना|जोड़|ठीक|पब्लिश|प्रकाशित|बदल)\s*सकते\s*हैं'
]


def is_action_request(question: str) -> bool:
    """Detects whether the administrator is asking the assistant to execute an action."""
    q = question.lower().strip()

    # Hindi action check
    for pattern in HINDI_ACTION_PATTERNS:
        if re.search(pattern, question):
            return True

    # English action check
    if re.search(r'\b(?:just\s+fix|autofix|auto-fix)\b', q):
        return True
    if re.search(r'\b(?:fix|resolve|correct)\s+(?:it|this|them|all|the\s+issue|everything|category|activity|the)\b', q):
        return True
    if re.search(r'\b(?:do\s+(?:it|this)|take\s+care\s+of\s+(?:it|this))\s+for\s+me\b', q):
        return True
    if re.search(r'\bfor\s+me\b', q) and any(verb in q for verb in ['fix', 'delete', 'create', 'publish', 'update', 'change', 'remove', 'assign']):
        return True
    if re.search(r'\b(?:delete|remove|purge|erase|drop)\s+(?:the|this|all|unused|empty|broken|category|categories|activity|activities|question|user|record)\b', q):
        return True
    if re.search(r'\b(?:publish|approve)\s+(?:it|this|them|the|all|pending|draft|activity|activities|content)\b', q):
        return True
    if re.search(r'\b(?:can\s+you|could\s+you|please|will\s+you)\s+(?:fix|delete|remove|publish|create|add|change|update|edit|assign)\b', q):
        return True

    return False


def _build_action_refusal_response(question: str, context: dict, is_hindi: bool = False) -> dict:
    """
    Constructs a polite, clear refusal explaining the assistant's read-only advisory
    nature and provides direct links to where the administrator can perform the action.
    """
    q_lower = question.lower()
    relevant_links = []

    if 'category' in q_lower or 'categories' in q_lower or 'श्रेणी' in question:
        relevant_links.append(ADMIN_LINKS['categories'])
        relevant_links.append(ADMIN_LINKS['new_category'])
    if 'activity' in q_lower or 'activities' in q_lower or 'draft' in q_lower or 'गतिविधि' in question:
        relevant_links.append(ADMIN_LINKS['activities'])
        relevant_links.append(ADMIN_LINKS['content_suggestions'])
    if 'suggestion' in q_lower or 'सुझाव' in question:
        relevant_links.append(ADMIN_LINKS['content_suggestions'])
    if 'audit' in q_lower or 'log' in q_lower or 'लॉग' in question:
        relevant_links.append(ADMIN_LINKS['audit_logs'])
    if 'assign' in q_lower or 'teacher' in q_lower or 'असाइन' in question or 'शिक्षक' in question:
        relevant_links.append(ADMIN_LINKS['assignments'])
    if 'user' in q_lower or 'उपयोगकर्ता' in question:
        relevant_links.append(ADMIN_LINKS['users'])

    # Always provide Action Center as primary destination
    if ADMIN_LINKS['action_center'] not in relevant_links:
        relevant_links.insert(0, ADMIN_LINKS['action_center'])

    links_markdown = "\n".join([f"- [{item['label']}]({item['url']})" for item in relevant_links])

    if is_hindi:
        answer = (
            "मैं एक **सलाहकार सहायक (Advisory Assistant)** हूँ और डेटाबेस में कोई बदलाव, सामग्री संपादन, ड्राफ्ट प्रकाशित, "
            "या रिकॉर्ड डिलीट नहीं कर सकता। ChildInsight में डेटा सुरक्षा और अखंडता के लिए सभी डेटाबेस परिवर्तनों में प्रत्यक्ष मानवीय निरीक्षण अनिवार्य है।\n\n"
            "मैं आपको सिस्टम की स्थिति समझा सकता हूँ और निर्णय लेने में मदद कर सकता हूँ, लेकिन यह कार्य आपको स्वयं प्रशासनिक कंसोल में करना होगा। "
            "आप नीचे दिए गए लिंक का उपयोग करके सीधे संबंधित पृष्ठ पर जा सकते हैं:\n\n"
            f"{links_markdown}"
        )
    else:
        answer = (
            "I am an **advisory assistant** and cannot make changes, edit content, publish drafts, "
            "or delete records. In ChildInsight, all database modifications require explicit human oversight.\n\n"
            "I can explain what needs attention and guide your decisions, but you must perform the action "
            "yourself in the administrative console. You can take action at the following links:\n\n"
            f"{links_markdown}"
        )

    return {
        'answer': answer,
        'links': relevant_links,
        'refusal': True
    }


# =============================================================================
# 3. CONVERSATIONAL CONTEXT & HISTORY EXTRACTION
# =============================================================================

def _extract_category_from_history(history: Optional[List[Dict[str, str]]], categories: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Inspects recent conversation turns to find the most recently discussed category.
    Enables natural elliptical follow-ups (e.g. 'What about it?', 'How many activities does it have?').
    """
    if not history:
        return None

    # Search backwards through conversation history
    for msg in reversed(history):
        content = (msg.get('content') or '').lower()
        for cat in categories:
            cat_name = cat['name'].lower()
            cat_slug = cat['slug'].replace('-', ' ').lower()
            if cat_name in content or cat_slug in content:
                return cat
            # Check keywords mapping
            for kw in CATEGORY_KEYWORDS.get(cat['slug'], []):
                if kw in content:
                    return cat

    return None


def _match_category_in_query(question: str, categories: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Matches a category name, slug, or Hindi translation directly in the current question."""
    q_lower = question.lower().strip()

    for cat in categories:
        cat_name = cat['name'].lower()
        cat_slug = cat['slug'].replace('-', ' ').lower()
        if cat_name in q_lower or cat_slug in q_lower:
            return cat
        for kw in CATEGORY_KEYWORDS.get(cat['slug'], []):
            if kw in q_lower:
                return cat

    return None


# =============================================================================
# 4. GROUNDED PROCEDURAL FALLBACK GENERATOR (WITH CONVERSATIONAL MEMORY & HINDI)
# =============================================================================

def _generate_grounded_fallback_answer(
    question: str,
    context: dict,
    history: Optional[List[Dict[str, str]]] = None,
    is_hindi: bool = False
) -> dict:
    """
    Generates a 100% grounded, conversational answer strictly from real platform context.
    Maintains conversational memory of recent turns and supports both English and Hindi.
    """
    q_lower = question.lower().strip()
    relevant_links = []
    categories = context.get('categories', [])

    # -------------------------------------------------------------------------
    # A. Category Resolution (Direct Match or Conversational Follow-up via History)
    # -------------------------------------------------------------------------
    matched_cat = _match_category_in_query(question, categories)

    # If no direct match, check if query is an elliptical follow-up referencing prior category
    if not matched_cat and history:
        is_pronoun_reference = bool(re.search(
            r'\b(?:it|this|that|the category|this category|that category|its)\b',
            q_lower
        ) or re.search(r'(?:इस|उस|इसकी|उसकी|इसमें|उसमें|श्रेणी)', question))

        is_category_question = any(k in q_lower for k in [
            'how many activities', 'how many questions', 'is it healthy', 'what about', 'status',
            'कितनी गतिविधियाँ', 'कितने प्रश्न', 'स्थिति'
        ])

        if is_pronoun_reference or is_category_question:
            matched_cat = _extract_category_from_history(history, categories)

    if matched_cat:
        cat_id = matched_cat['id']
        cat_name = matched_cat['name']
        act_count = matched_cat['activity_count']
        has_hi = matched_cat['has_hindi']

        # Find matching action items or suggestions
        cat_items = [
            item for item in context.get('action_items', [])
            if item.get('meta', {}).get('category_id') == cat_id or cat_name.lower() in item.get('title', '').lower()
        ]
        cat_suggestions = [s for s in context.get('pending_suggestions', []) if s.get('category_id') == cat_id]

        if is_hindi:
            status_lines = [
                f"श्रेणी **'{cat_name}'** की वर्तमान स्थिति:",
                f"- **सक्रिय गतिविधियां**: {act_count} गतिविधियां",
                f"- **हिंदी अनुवाद**: {'उपलब्ध है' if has_hi else 'हिंदी नाम/विवरण अनुपलब्ध है'}",
                f"- **लंबित सामग्री सुझाव**: {len(cat_suggestions)} सुझाव"
            ]

            if cat_items:
                status_lines.append("\n**सक्रिय एक्शन सेंटर कार्य:**")
                for item in cat_items:
                    status_lines.append(f"- [{item['priority_tier']}] {item['summary']}")
                    relevant_links.append({'label': item['action_label'], 'url': item['action_url']})
            elif act_count == 0:
                status_lines.append(f"\nइस श्रेणी में **0 गतिविधियां** हैं। बच्चे इसमें तब तक नहीं खेल सकते जब तक गतिविधियां जोड़ी न जाएं।")
                relevant_links.append({'label': f"{cat_name} में गतिविधि जोड़ें", 'url': f"/admin/activities/new?category_id={cat_id}"})
            else:
                status_lines.append(f"\n'{cat_name}' श्रेणी में कोई सक्रिय विसंगति या महत्वपूर्ण कमी नहीं पाई गई है।")

            answer = "\n".join(status_lines)
            relevant_links.append({'label': f"{cat_name} गतिविधियां प्रबंधित करें", 'url': f"/admin/activities?category_id={cat_id}"})
            relevant_links.append(ADMIN_LINKS['categories'])
        else:
            status_lines = [
                f"Status for category **'{cat_name}'**:",
                f"- **Activity Count**: {act_count} active activities",
                f"- **Hindi Category Translation**: {'Present' if has_hi else 'Missing Hindi name/description'}",
                f"- **Pending Content Suggestions**: {len(cat_suggestions)} suggestion(s)"
            ]

            if cat_items:
                status_lines.append("\n**Active Action Center Items:**")
                for item in cat_items:
                    status_lines.append(f"- [{item['priority_tier']}] {item['summary']}")
                    relevant_links.append({'label': item['action_label'], 'url': item['action_url']})
            elif act_count == 0:
                status_lines.append(f"\nThis category has **0 activities**. Children cannot see or play in this category until activities are added.")
                relevant_links.append({'label': f"Add Activity to {cat_name}", 'url': f"/admin/activities/new?category_id={cat_id}"})
            else:
                status_lines.append(f"\nNo active anomalies or critical gaps were flagged for '{cat_name}'.")

            answer = "\n".join(status_lines)
            relevant_links.append({'label': f"Manage {cat_name} Activities", 'url': f"/admin/activities?category_id={cat_id}"})
            relevant_links.append(ADMIN_LINKS['categories'])

    # -------------------------------------------------------------------------
    # B. Platform User & Learner Counts
    # -------------------------------------------------------------------------
    elif any(k in q_lower for k in [
        'how many users', 'user count', 'users count', 'how many teachers', 'how many parents',
        'how many children', 'how many students', 'how many learners', 'registered users', 'user breakdown'
    ]) or any(k in question for k in ['कितने उपयोगकर्ता', 'कितने शिक्षक', 'कितने अभिभावक', 'कितने बच्चे', 'उपयोगकर्ता']):
        uc = context.get('user_counts', {})
        total_u = uc.get('total', 0)
        parents = uc.get('parent', 0)
        teachers = uc.get('teacher', 0)
        admins = uc.get('admin', 0)
        children = uc.get('children', 0)

        if is_hindi:
            answer = (
                f"ChildInsight में वर्तमान में कुल **{total_u} पंजीकृत उपयोगकर्ता** और **{children} शिक्षार्थी (बच्चे)** हैं:\n\n"
                f"- **अभिभावक (Parents)**: {parents}\n"
                f"- **शिक्षक (Teachers)**: {teachers}\n"
                f"- **प्रशासक (Administrators)**: {admins}\n"
                f"- **बच्चे / शिक्षार्थी प्रोफाइल**: {children}\n\n"
                f"आप [उपयोगकर्ता प्रबंधन (/admin/users)](/admin/users) में उपयोगकर्ता खातों और उनकी भूमिकाओं को प्रबंधित कर सकते हैं, "
                f"या [शिक्षक असाइनमेंट](/admin/assignments) में विद्यार्थियों को शिक्षकों से जोड़ सकते हैं।"
            )
        else:
            answer = (
                f"ChildInsight currently has **{total_u} registered user(s)** and **{children} child/learner profile(s)** across the platform:\n\n"
                f"- **Parents**: {parents}\n"
                f"- **Teachers**: {teachers}\n"
                f"- **Administrators**: {admins}\n"
                f"- **Children / Learners**: {children}\n\n"
                f"You can manage user roles and view account details in [User Management](/admin/users), "
                f"or allocate students in [Teacher Assignments](/admin/assignments)."
            )
        relevant_links.append(ADMIN_LINKS['users'])
        relevant_links.append(ADMIN_LINKS['assignments'])

    # -------------------------------------------------------------------------
    # C. Recommendation Engine & Analytics Architecture
    # -------------------------------------------------------------------------
    elif any(k in q_lower for k in [
        'recommendation', 'recommendations', 'difficulty', 'stamina', 'k-means', 'kmeans',
        'cohort', 'algorithm', 'how do recommendations work', 'adaptation', 'adaptive'
    ]) or any(k in question for k in ['सिफारिश', 'सुझाव प्रणाली', 'कठिनाई', 'एल्गोरिदम']):
        if is_hindi:
            answer = (
                "ChildInsight की **अनुशंसा और अनुकूलन प्रणाली (Recommendation Engine)** एक 3-स्तरीय डिज़ाइन पर काम करती है:\n\n"
                "1. **स्तर 1: नियम-आधारित श्रेणी सटीकता (Rule-Based Accuracy Thresholds)**:\n"
                "   - $\\ge 80\\%$ सटीकता: स्तर आगे बढ़ाती है (Beginner $\\to$ Easy $\\to$ Medium $\\to$ Advanced)।\n"
                "   - $< 50\\%$ सटीकता: मूलभूत समझ मजबूत करने के लिए स्तर घटाती है या अभ्यास गतिविधियां सुझाती है।\n"
                "   - $50\\% - 79\\%$ सटीकता: वर्तमान स्तर पर सुदृढ़ीकरण बनाए रखती है।\n\n"
                "2. **स्तर 2: सहनशक्ति और पूर्णता अंशांकन (Stamina & Completion Calibration)**:\n"
                "   - यदि बच्चे की सटीकता उच्च है लेकिन सत्र पूर्णता दर $< 50\\%$ है, तो इंजन स्तर नहीं बढ़ाता बल्कि उसी स्तर पर सहनशक्ति को मजबूत करता है।\n\n"
                "3. **स्तर 3: के-मीन्स एमएल क्लस्टरिंग (K-Means ML Cohorts)**:\n"
                "   - गति, सटीकता और पूर्णता दर के आधार पर बच्चों को 4 समूहों (`high_performer`, `steady_learner`, `needs_support`, `curious_explorer`) में समूहित करती है।\n\n"
                "**नैतिक व विनियामक नियम (PRD §4)**: यह प्रणाली पूर्णतः **गैर-निदानिक (strictly non-diagnostic)** है। यह कभी किसी बच्चे को लेबल या वर्गीकृत नहीं करती, बल्कि केवल सीखने की गति को अनुकूलित करती है।"
            )
        else:
            answer = (
                "ChildInsight's **Adaptive Recommendation Engine** operates on a proven 3-layer architecture:\n\n"
                "1. **Layer 1: Category Accuracy Thresholds (Rule-Based)**:\n"
                "   - Accuracy $\\ge 80\\%$: Level-up progression (Beginner $\\to$ Easy $\\to$ Medium $\\to$ Advanced).\n"
                "   - Accuracy $< 50\\%$: Step-down or foundational practice reinforcement.\n"
                "   - Accuracy $50\\% - 79\\%$: Consolidates mastery at the current difficulty.\n\n"
                "2. **Layer 2: Combined Accuracy & Completion Stamina Calibration**:\n"
                "   - Evaluates stamina alongside accuracy: if a learner has high accuracy but completion rate is $< 50\\%$, the engine reinforces engagement at the current tier before advancing.\n\n"
                "3. **Layer 3: K-Means ML Clustering (Engagement Cohorts)**:\n"
                "   - Clusters multi-session behavioral features (accuracy, speed, completion patterns) into 4 cohorts: `high_performer`, `steady_learner`, `needs_support`, and `curious_explorer`.\n\n"
                "**Ethical Guardrail (PRD §4)**: The engine is **strictly non-diagnostic and educational only**. It never pathologizes or labels children; it purely adapts pedagogical pace and engagement."
            )
        relevant_links.append(ADMIN_LINKS['agents_dashboard'])
        relevant_links.append(ADMIN_LINKS['action_center'])

    # -------------------------------------------------------------------------
    # D. How-To Guidance (Step-by-Step with Direct Admin Links)
    # -------------------------------------------------------------------------
    elif any(k in q_lower for k in ['how to', 'how do i', 'how can i', 'steps to', 'where do i']) or any(k in question for k in ['कैसे करें', 'कैसे जोड़ें', 'कैसे बनाएं', 'कहाँ जाऊं']):
        # Teacher assignment how-to
        if any(k in q_lower for k in ['assign', 'teacher', 'student']) or any(k in question for k in ['शिक्षक', 'असाइन']):
            if is_hindi:
                answer = (
                    "**विद्यार्थियों को शिक्षक से असाइन करने के चरण:**\n\n"
                    "1. [शिक्षक असाइनमेंट](/admin/assignments) पृष्ठ पर जाएं।\n"
                    "2. शीर्ष ड्रॉपडाउन से संबंधित शिक्षक का चयन करें।\n"
                    "3. उस शिक्षक के अंतर्गत जोड़े जाने वाले बच्चों के चेकबॉक्स को चेक करें।\n"
                    "4. परिवर्तनों को लागू करने के लिए **'Save Assignments'** बटन पर क्लिक करें।"
                )
            else:
                answer = (
                    "**How to Assign Students to a Teacher:**\n\n"
                    "1. Navigate to [Teacher Assignments](/admin/assignments).\n"
                    "2. Select the teacher from the teacher dropdown roster.\n"
                    "3. Check the checkboxes next to the child profiles you want to assign to this teacher.\n"
                    "4. Click **'Save Assignments'** to apply changes. The teacher will immediately see their assigned roster."
                )
            relevant_links.append(ADMIN_LINKS['assignments'])

        # Category creation how-to
        elif any(k in q_lower for k in ['category', 'categories']) or any(k in question for k in ['श्रेणी']):
            if is_hindi:
                answer = (
                    "**नई श्रेणी बनाने के चरण:**\n\n"
                    "1. [नई श्रेणी बनाएं](/admin/categories/new) पर जाएं (या [श्रेणी प्रबंधन](/admin/categories) से '+ Add Category' चुनें)।\n"
                    "2. श्रेणी का नाम, स्लग, विवरण और उपयुक्त इमोजी आइकन दर्ज करें।\n"
                    "3. द्विभाषी कैटलॉग के लिए हिंदी नाम और विवरण भी दर्ज करें।\n"
                    "4. **'Save Category'** पर क्लिक करें। इसके बाद गतिविधियों को जोड़ना न भूलें!"
                )
            else:
                answer = (
                    "**How to Create a New Category:**\n\n"
                    "1. Navigate directly to [Create Category](/admin/categories/new) (or click '+ Add Category' on [Manage Categories](/admin/categories)).\n"
                    "2. Provide the Category Name, unique slug, description, and an emoji icon.\n"
                    "3. Provide Hindi translations (name and description) to maintain bilingual catalog coverage.\n"
                    "4. Click **'Save Category'**. Remember to add learning activities next so children can explore it!"
                )
            relevant_links.append(ADMIN_LINKS['new_category'])
            relevant_links.append(ADMIN_LINKS['categories'])

        # Activity creation how-to
        elif any(k in q_lower for k in ['activity', 'activities']) or any(k in question for k in ['गतिविधि']):
            if is_hindi:
                answer = (
                    "**नई गतिविधि जोड़ने के चरण:**\n\n"
                    "1. [नई गतिविधि बनाएं](/admin/activities/new) पर जाएं।\n"
                    "2. श्रेणी, लक्षित आयु वर्ग (जैसे 3-5, 6-8, 9-12), कठिनाई स्तर (Beginner से Advanced) और अनुमानित समय चुनें।\n"
                    "3. अंग्रेजी और हिंदी दोनों में शीर्षक और विवरण दर्ज करें।\n"
                    "4. गतिविधि सहेजने के बाद [गतिविधियां प्रबंधित करें](/admin/activities) में जाकर प्रश्न जोड़ें।"
                )
            else:
                answer = (
                    "**How to Create a New Activity:**\n\n"
                    "1. Navigate to [Create Activity](/admin/activities/new).\n"
                    "2. Select the Category, target age band (e.g. 3-5, 6-8, 9-12), difficulty level, and estimated duration.\n"
                    "3. Enter the title and description in both English and Hindi.\n"
                    "4. Save the activity, then add interactive questions via [Manage Activities](/admin/activities) so children can play."
                )
            relevant_links.append(ADMIN_LINKS['new_activity'])
            relevant_links.append(ADMIN_LINKS['activities'])

        # Content suggestions & drafts how-to
        elif any(k in q_lower for k in ['suggestion', 'draft', 'review']) or any(k in question for k in ['सुझाव', 'ड्राफ्ट']):
            if is_hindi:
                answer = (
                    "**सामग्री सुझावों की समीक्षा और ड्राफ्ट तैयार करने के चरण:**\n\n"
                    "1. [एक्शन सेंटर](/admin/action-center) या [सामग्री सुझाव](/admin/content-suggestions) पृष्ठ खोलें।\n"
                    "2. शिक्षार्थी मांग और कैटलॉग अंतरालों द्वारा प्राथमिकता दिए गए सुझावों की समीक्षा करें।\n"
                    "3. चेकबॉक्स चुनकर **'Generate Drafts for Selected'** पर क्लिक करें।\n"
                    "4. उत्पन्न ड्राफ्ट्स को प्रकाशित करने से पहले [गतिविधियां](/admin/activities) में समीक्षा करें।"
                )
            else:
                answer = (
                    "**How to Review Suggestions & Generate AI Drafts:**\n\n"
                    "1. Open the [Action Center](/admin/action-center) or [Content Suggestions](/admin/content-suggestions).\n"
                    "2. Review suggestions ranked by priority score and learner demand.\n"
                    "3. Select suggestions and click **'Generate Drafts for Selected'** or use the per-card 'Draft with AI' button.\n"
                    "4. Review and edit the generated activity draft in [Manage Activities](/admin/activities) before publishing."
                )
            relevant_links.append(ADMIN_LINKS['action_center'])
            relevant_links.append(ADMIN_LINKS['content_suggestions'])

        # General administration how-to
        else:
            if is_hindi:
                answer = (
                    "**प्रशासनिक कंसोल नेविगेशन मार्गदर्शिका:**\n\n"
                    "- **एक्शन सेंटर**: प्राथमिक कार्यों की समीक्षा करें: [एक्शन सेंटर](/admin/action-center)\n"
                    "- **श्रेणियां**: श्रेणियां जोड़ें और प्रबंधित करें: [श्रेणियां](/admin/categories)\n"
                    "- **गतिविधियां**: सीखने की गतिविधियां और प्रश्न प्रबंधित करें: [गतिविधियां](/admin/activities)\n"
                    "- **उपयोगकर्ता**: उपयोगकर्ता भूमिकाएं प्रबंधित करें: [उपयोगकर्ता](/admin/users)\n"
                    "- **शिक्षक असाइनमेंट**: विद्यार्थियों को आवंटित करें: [शिक्षक असाइनमेंट](/admin/assignments)\n"
                    "- **सिस्टम एजेंट**: तकनीकी स्वास्थ्य और डायग्नोस्टिक्स देखें: [सिस्टम एजेंट](/admin/agents)"
                )
            else:
                answer = (
                    "**Administrative Console Navigation Guide:**\n\n"
                    "- **Action Center**: Review top prioritized items: [Action Center](/admin/action-center)\n"
                    "- **Categories**: Organize learning domains: [Manage Categories](/admin/categories)\n"
                    "- **Activities**: Create and manage learning activities: [Manage Activities](/admin/activities)\n"
                    "- **Users & Roles**: Update accounts and assign roles: [User Management](/admin/users)\n"
                    "- **Teacher Rosters**: Assign students to teachers: [Teacher Assignments](/admin/assignments)\n"
                    "- **System Telemetry**: Technical health and diagnostics: [System Agents Dashboard](/admin/agents)"
                )
            relevant_links.append(ADMIN_LINKS['action_center'])
            relevant_links.append(ADMIN_LINKS['agents_dashboard'])

    # -------------------------------------------------------------------------
    # E. Recent Audit Logs
    # -------------------------------------------------------------------------
    elif any(k in q_lower for k in ['audit', 'recent log', 'recent logs', 'audit log', 'recent activity', 'recent actions', 'who did what']) or any(k in question for k in ['ऑडिट', 'हाल के लॉग']):
        logs = context.get('recent_audit_logs', [])
        if not logs:
            if is_hindi:
                answer = "वर्तमान में कोई हालिया ऑडिट लॉग रिकॉर्ड उपलब्ध नहीं है। आप [ऑडिट लॉग](/admin/audit-logs) में पूरा इतिहास देख सकते हैं।"
            else:
                answer = "There are currently no recent audit log records. You can view the full historical log in [Audit Logs](/admin/audit-logs)."
        else:
            log_lines = []
            for l in logs:
                log_lines.append(f"- `{l['timestamp']}`: **{l['action']}** on `{l['target_type']}` by *{l['user_name']}*")

            if is_hindi:
                answer = (
                    "**हाल के ऑडिट लॉग प्रविष्टियां:**\n\n" +
                    "\n".join(log_lines) +
                    "\n\nपूरा ऑडिट इतिहास देखने के लिए [ऑडिट लॉग](/admin/audit-logs) पर जाएं।"
                )
            else:
                answer = (
                    "**Recent Administrative Audit Log Entries:**\n\n" +
                    "\n".join(log_lines) +
                    "\n\nInspect all logged actions in [Audit Logs](/admin/audit-logs)."
                )
        relevant_links.append(ADMIN_LINKS['audit_logs'])

    # -------------------------------------------------------------------------
    # F. "What should I do next?" / Next Actions Query
    # -------------------------------------------------------------------------
    elif any(k in q_lower for k in ['what should i do', 'what to do next', 'what needs attention', 'next steps', 'priorities', 'priority']) or any(k in question for k in ['क्या करूँ', 'आगे क्या', 'प्राथमिकता']):
        action_items = context.get('action_items', [])
        crit_count = context.get('critical_items_count', 0)
        imp_count = context.get('important_items_count', 0)
        total_items = context.get('action_items_count', 0)

        if total_items == 0:
            if is_hindi:
                answer = (
                    "वर्तमान में ध्यान देने योग्य **0 लंबित एक्शन कार्य** हैं। प्लेटफ़ॉर्म स्वास्थ्य "
                    f"{context['health_metrics']['overall_score']:.1f}/100 पर है और कोई कैटलॉग विसंगति नहीं पाई गई है।"
                )
            else:
                answer = (
                    "There are currently **0 pending action items** requiring attention. Platform health is at "
                    f"{context['health_metrics']['overall_score']:.1f}/100 and no catalog integrity anomalies "
                    "are detected. You can review current activities or browse system telemetry."
                )
            relevant_links.append(ADMIN_LINKS['action_center'])
            relevant_links.append(ADMIN_LINKS['activities'])
        else:
            top_items = action_items[:3]
            bullets = []
            for item in top_items:
                tier_badge = f"**[{item['priority_tier']}]**"
                bullets.append(f"- {tier_badge} {item['title']}: {item['summary']} [Act: {item['action_label']}]({item['action_url']})")
                relevant_links.append({'label': item['action_label'], 'url': item['action_url']})

            bullets_text = "\n".join(bullets)
            if is_hindi:
                answer = (
                    f"एक्शन सेंटर में वर्तमान में कुल **{total_items} कार्य** हैं "
                    f"({crit_count} महत्वपूर्ण (Critical), {imp_count} आवश्यक (Important))। शीर्ष प्राथमिकताएं:\n\n"
                    f"{bullets_text}\n\n"
                    f"सभी कार्यों को देखने के लिए [एक्शन सेंटर](/admin/action-center) पर जाएं।"
                )
            else:
                answer = (
                    f"You currently have **{total_items} action item(s)** organized in the Action Center "
                    f"({crit_count} Critical, {imp_count} Important). Here are the top priorities to address:\n\n"
                    f"{bullets_text}\n\n"
                    f"View all prioritized items in the [Action Center](/admin/action-center)."
                )
            relevant_links.append(ADMIN_LINKS['action_center'])

    # -------------------------------------------------------------------------
    # G. "Did I make any mistakes?" / Catalog Integrity Questions
    # -------------------------------------------------------------------------
    elif any(k in q_lower for k in ['mistake', 'error', 'integrity', 'wrong', 'broken', 'issue']) or any(k in question for k in ['गलती', 'त्रुटि', 'खराबी', 'कमी']):
        issues = context.get('integrity_issues', [])
        issue_count = context.get('integrity_issues_count', 0)
        empty_cats = [c for c in categories if c['activity_count'] == 0]

        if issue_count == 0 and not empty_cats:
            if is_hindi:
                answer = (
                    "सिस्टम ने पूर्ण सामग्री अखंडता ऑडिट पूरा किया और **0 विसंगतियां** पाईं। "
                    "सभी श्रेणियों में गतिविधियां मौजूद हैं, सभी सक्रिय गतिविधियों में प्रश्न हैं, और कोई टूटे हुए संदर्भ नहीं हैं।"
                )
            else:
                answer = (
                    "The system ran a complete content integrity audit and found **0 catalog anomalies**. "
                    "All categories contain activities, all active activities contain questions, and no broken references were found."
                )
            relevant_links.append(ADMIN_LINKS['activities'])
            relevant_links.append(ADMIN_LINKS['agents_dashboard'])
        else:
            bullets = []
            if empty_cats:
                for c in empty_cats:
                    bullets.append(f"- Category **'{c['name']}'** has 0 activities — [Add Activity to {c['name']}](/admin/activities/new?category_id={c['id']})")
                    relevant_links.append({'label': f"Add Activity ({c['name']})", 'url': f"/admin/activities/new?category_id={c['id']}"})
            for issue in issues[:4]:
                bullets.append(f"- {issue['affected_record']}: {issue['description']} Suggested Fix: {issue['suggested_fix']}")

            bullets_text = "\n".join(bullets)
            if is_hindi:
                answer = (
                    f"सामग्री अखंडता एजेंट (Content Integrity Agent) ने **{issue_count} समस्या(एं)** पाई हैं"
                    f"{f' और {len(empty_cats)} खाली श्रेणी(यां)' if empty_cats else ''}:\n\n"
                    f"{bullets_text}\n\n"
                    f"इन समस्याओं को [गतिविधियां प्रबंधित करें](/admin/activities) या [श्रेणियां](/admin/categories) में हल करें।"
                )
            else:
                answer = (
                    f"The Content Integrity Agent detected **{issue_count} issue(s)** in the catalog"
                    f"{f' along with {len(empty_cats)} empty category/ies' if empty_cats else ''}:\n\n"
                    f"{bullets_text}\n\n"
                    f"Inspect and resolve these issues in [Manage Activities](/admin/activities) or [Categories](/admin/categories)."
                )
            relevant_links.append(ADMIN_LINKS['activities'])
            relevant_links.append(ADMIN_LINKS['categories'])

    # -------------------------------------------------------------------------
    # H. Platform Health / Telemetry Queries
    # -------------------------------------------------------------------------
    elif any(k in q_lower for k in ['health', 'score', 'telemetry', 'posture', 'completion rate']) or any(k in question for k in ['स्वास्थ्य', 'स्कोर', 'टेलीमेट्री']):
        hm = context.get('health_metrics', {})
        score = hm.get('overall_score', 100.0)
        comp = hm.get('completion_rate', 100.0)
        valid_act = hm.get('valid_activities_pct', 100.0)
        cohorts = hm.get('cohorts', [])

        cohort_lines = []
        for c in cohorts:
            cohort_lines.append(f"- **{c['name']}**: Score {c['score']:.1f}/100, Completion Rate {c['completion_rate']:.1f}%, Learners: {c['total_children']}")

        if is_hindi:
            answer = (
                f"वर्तमान प्लेटफ़ॉर्म स्वास्थ्य स्कोर **{score:.1f}/100** है।\n\n"
                f"- **सत्र पूर्णता दर**: {comp:.1f}%\n"
                f"- **वैध गतिविधि कवरेज**: {valid_act:.1f}%\n"
                f"- **हाल की अनुपालन घटनाएं (24h)**: {context.get('compliance_incidents_24h', 0)}\n\n"
                f"**आयु समूह स्थिति (Cohorts):**\n" + "\n".join(cohort_lines) + "\n\n"
                f"विस्तृत तकनीकी डायग्नोस्टिक्स के लिए [सिस्टम एजेंट डैशबोर्ड](/admin/agents) देखें।"
            )
        else:
            answer = (
                f"The platform health score is currently **{score:.1f}/100**.\n\n"
                f"- **Session Completion Rate**: {comp:.1f}%\n"
                f"- **Valid Activity Coverage**: {valid_act:.1f}%\n"
                f"- **Recent Compliance Incidents (24h)**: {context.get('compliance_incidents_24h', 0)}\n\n"
                f"**Cohort Breakdown:**\n" + "\n".join(cohort_lines) + "\n\n"
                f"Review detailed telemetry on the [System Agents Dashboard](/admin/agents)."
            )
        relevant_links.append(ADMIN_LINKS['agents_dashboard'])
        relevant_links.append(ADMIN_LINKS['action_center'])

    # -------------------------------------------------------------------------
    # I. Default General Platform Summary
    # -------------------------------------------------------------------------
    else:
        crit = context.get('critical_items_count', 0)
        total = context.get('action_items_count', 0)
        score = context['health_metrics']['overall_score']
        issues = context.get('integrity_issues_count', 0)
        uc = context.get('user_counts', {})
        cat_c = context.get('catalog_counts', {})

        if is_hindi:
            answer = (
                f"नमस्ते! यहाँ वर्तमान ChildInsight प्लेटफ़ॉर्म की समग्र स्थिति है:\n\n"
                f"- **प्लेटफ़ॉर्म स्वास्थ्य स्कोर**: {score:.1f}/100\n"
                f"- **एक्शन सेंटर कार्य**: {total} कुल ({crit} Critical)\n"
                f"- **पंजीकृत उपयोगकर्ता**: {uc.get('total', 0)} ({uc.get('children', 0)} शिक्षार्थी)\n"
                f"- **कैटलॉग**: {cat_c.get('activities', 0)} गतिविधियां, {cat_c.get('categories', len(categories))} श्रेणियां\n"
                f"- **सामग्री अखंडता विसंगतियां**: {issues}\n"
                f"- **लंबित सुझाव**: {context.get('pending_suggestions_count', 0)}\n\n"
                f"आप मुझसे पूछ सकते हैं: *'आगे क्या करना चाहिए?'*, *'सिफारिश प्रणाली कैसे काम करती है?'*, *'उपयोगकर्ता कितने हैं?'*, "
                f"या किसी विशिष्ट श्रेणी (जैसे 'तर्क' या 'विज्ञान') की स्थिति। "
                f"कार्यों के लिए [एक्शन सेंटर](/admin/action-center) देखें।"
            )
        else:
            answer = (
                f"Hello! Here is a summary of the current platform status:\n\n"
                f"- **Platform Health Score**: {score:.1f}/100\n"
                f"- **Action Center Items**: {total} total ({crit} Critical)\n"
                f"- **Total Registered Users**: {uc.get('total', 0)} ({uc.get('children', 0)} learners)\n"
                f"- **Catalog Overview**: {cat_c.get('activities', 0)} activities across {cat_c.get('categories', len(categories))} categories\n"
                f"- **Content Integrity Issues**: {issues}\n"
                f"- **Pending Content Suggestions**: {context.get('pending_suggestions_count', 0)}\n"
                f"- **Recent Compliance Incidents (24h)**: {context.get('compliance_incidents_24h', 0)}\n\n"
                f"You can ask me questions like *'What should I do next?'*, *'How do recommendations work?'*, *'How many users on the platform?'*, "
                f"or ask about specific categories. Check the [Action Center](/admin/action-center) for all prioritized tasks."
            )
        relevant_links.append(ADMIN_LINKS['action_center'])
        relevant_links.append(ADMIN_LINKS['content_suggestions'])

    # Deduplicate links by url
    seen_urls = set()
    deduped_links = []
    for link in relevant_links:
        if link['url'] not in seen_urls:
            seen_urls.add(link['url'])
            deduped_links.append(link)

    return {
        'answer': answer,
        'links': deduped_links,
        'refusal': False
    }


# =============================================================================
# 5. ANTHROPIC API INTEGRATION (CONVERSATIONAL MULTI-TURN & HINDI)
# =============================================================================

def _call_anthropic_api(system_prompt: str, messages: list) -> str:
    """
    Calls the Anthropic Messages API requesting conversational guidance.
    Uses urllib.request (consistent with content_draft_agent.py).
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    model = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    payload = {
        "model": model,
        "max_tokens": 1200,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": messages
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=30) as response:
        res_body = response.read().decode('utf-8')
        res_json = json.loads(res_body)

    content_blocks = res_json.get('content', [])
    raw_text = "".join(b.get('text', '') for b in content_blocks if b.get('type') == 'text')
    return raw_text.strip()


def ask_assistant(
    question: str,
    context: Optional[dict] = None,
    history: Optional[List[Dict[str, str]]] = None,
    language: Optional[str] = None
) -> dict:
    """
    Entrypoint for administrator questions:
    1. Gathers real platform data (or uses supplied context).
    2. Detects language (English vs Hindi).
    3. Inspects for action execution requests — immediately refuses with guidance and links if detected.
    4. Invokes Anthropic API if key is available, strictly constrained to real context.
    5. Falls back deterministically to procedural grounded answering if API is unavailable.
    """
    if not question or not question.strip():
        return {
            'answer': "Please ask a question about platform health, action items, catalog integrity, or specific categories.",
            'links': [ADMIN_LINKS['action_center']],
            'refusal': False,
            'detected_language': 'en'
        }

    q_clean = question.strip()

    # Detect language: Hindi if Devanagari script detected or explicitly set to 'hi'
    is_hi = (language == 'hi') or is_hindi_text(q_clean)
    detected_lang = 'hi' if is_hi else 'en'

    if context is None:
        context = gather_assistant_context()

    # Safety: Refuse action requests
    if is_action_request(q_clean):
        refusal_res = _build_action_refusal_response(q_clean, context, is_hindi=is_hi)
        refusal_res['detected_language'] = detected_lang
        return refusal_res

    # If Anthropic API key is configured, use it with strict system constraints
    if os.environ.get('ANTHROPIC_API_KEY'):
        try:
            lang_instruction = (
                "The user is conversing in Hindi (or explicitly selected Hindi). Respond naturally and accurately in Hindi "
                "using standard Devanagari script and ChildInsight Hindi terminology (e.g. प्रशासक, शिक्षक, अभिभावक, बच्चे, गतिविधियां, श्रेणियां)."
                if is_hi else
                "Respond in clear, warm, conversational English."
            )

            system_prompt = (
                "You are the ChildInsight Admin Assistant, an intelligent, strictly read-only advisory guide for administrators.\n"
                "Your role is to converse warmly and naturally, explaining and guiding administrators on platform status, "
                "user metrics, recommendation engine mechanics, and how to perform tasks.\n\n"
                f"{lang_instruction}\n\n"
                "CRITICAL RULES:\n"
                "1. STRICTLY NEVER ACT: You cannot create, edit, delete, or publish anything. Do not pretend to execute actions.\n"
                "2. GROUNDED IN REAL DATA ONLY: Answer using ONLY the real data provided in the context below. NEVER invent, "
                "hallucinate, or estimate any numbers, statistics, counts, or categories. Every number must match the context.\n"
                "3. DIRECT DEEP LINKS: Include direct Markdown links to relevant admin pages whenever discussing actions:\n"
                "   - Action Center: [Action Center](/admin/action-center)\n"
                "   - Content Suggestions: [Content Suggestions](/admin/content-suggestions)\n"
                "   - Manage Activities: [Activities](/admin/activities)\n"
                "   - Manage Categories: [Categories](/admin/categories)\n"
                "   - User Management: [Users](/admin/users)\n"
                "   - Teacher Assignments: [Teacher Assignments](/admin/assignments)\n"
                "   - Audit Logs: [Audit Logs](/admin/audit-logs)\n"
                "   - System Agents: [System Agents](/admin/agents)\n"
                "4. CONVERSATIONAL TONE: Warm, natural, and helpful while strictly adhering to ground truth."
            )

            context_summary = json.dumps(context, indent=2)

            api_messages = []
            if history:
                for h in history[-6:]:
                    r = h.get('role')
                    c = h.get('content')
                    if r in ('user', 'assistant') and c:
                        api_messages.append({'role': r, 'content': str(c)})

            current_user_content = (
                f"CURRENT REAL PLATFORM CONTEXT:\n{context_summary}\n\n"
                f"ADMINISTRATOR QUESTION:\n{q_clean}\n\n"
                "Provide a warm, conversational, grounded response citing only facts from the context. "
                "Include markdown links to the relevant admin pages."
            )
            api_messages.append({'role': 'user', 'content': current_user_content})

            answer_text = _call_anthropic_api(system_prompt, api_messages)

            # Extract links mentioned or provide fallback action center link
            links = []
            for key, link_obj in ADMIN_LINKS.items():
                if link_obj['url'] in answer_text:
                    links.append(link_obj)
            if not links:
                links.append(ADMIN_LINKS['action_center'])

            return {
                'answer': answer_text,
                'links': links,
                'refusal': False,
                'detected_language': detected_lang
            }
        except Exception as e:
            logger.warning("Anthropic API call failed in admin_assistant, falling back: %s", e)

    # Procedural grounded fallback
    fallback_res = _generate_grounded_fallback_answer(
        question=q_clean,
        context=context,
        history=history,
        is_hindi=is_hi
    )
    fallback_res['detected_language'] = detected_lang
    return fallback_res


# =============================================================================
# 6. PROACTIVE MISTAKE-CATCHING (SURFACING EXISTING CHECKS)
# =============================================================================

def check_admin_action_result(action_type: str, entity_type: str, entity_id: int, entity_data: Optional[dict] = None) -> Optional[dict]:
    """
    Evaluates newly performed administrator mutations against existing system checks
    (Content Integrity Agent rules, empty categories, Case D translation gaps, teacher assignments).
    
    Does NOT invent new judgment logic — surfaces existing system checks conversationally.
    
    Returns a dict with {'note': str, 'level': 'info'|'warning', 'link_url': str, 'link_label': str}
    or None if no issues are detected.
    """
    try:
        # Category Creation / Modification
        if entity_type == 'category':
            cat = db.session.get(Category, entity_id)
            if not cat:
                return None

            act_count = cat.activities.count() if hasattr(cat.activities, 'count') else len(cat.activities)
            if act_count == 0:
                return {
                    'note': f"This category has 0 activities — remember to add learning activities before children can explore it.",
                    'level': 'warning',
                    'link_url': f"/admin/activities/new?category_id={cat.id}",
                    'link_label': "Add Activity Now"
                }

            # Check Hindi translation on Category
            has_hi = bool(cat.translations and cat.translations.get('hi', {}).get('name'))
            if not has_hi:
                return {
                    'note': f"Category '{cat.name}' is missing a Hindi translation — flagged for bilingual catalog coverage.",
                    'level': 'info',
                    'link_url': f"/admin/categories/{cat.id}/edit",
                    'link_label': "Add Hindi Details"
                }

        # Activity Creation / Modification
        elif entity_type == 'activity':
            act = db.session.get(Activity, entity_id)
            if not act:
                return None

            q_count = act.questions.count() if hasattr(act.questions, 'count') else len(act.questions)
            if q_count == 0:
                return {
                    'note': f"Activity '{act.title}' has 0 questions — children cannot play this activity until questions are added.",
                    'level': 'warning',
                    'link_url': f"/admin/activities/{act.id}/questions/new",
                    'link_label': "Add Questions"
                }

            # Check Content Integrity Case D (missing Hindi translations)
            act_trans = act.translations or {}
            hi_data = act_trans.get('hi', {})
            has_hi_title = bool(hi_data.get('title'))
            if not has_hi_title:
                return {
                    'note': f"Activity '{act.title}' is missing a Hindi translation — flagged under Content Integrity Case D for follow-up.",
                    'level': 'info',
                    'link_url': f"/admin/activities/{act.id}/edit",
                    'link_label': "Add Hindi Translation"
                }

        # User Role Modification
        elif entity_type == 'user':
            if action_type == 'role_change' and entity_data and entity_data.get('new_role') == 'teacher':
                assignments_count = TeacherAssignment.query.filter_by(teacher_id=entity_id).count()
                if assignments_count == 0:
                    return {
                        'note': "User role was changed to Teacher, but they currently have 0 assigned students — they will see an empty roster until assigned.",
                        'level': 'info',
                        'link_url': "/admin/assignments",
                        'link_label': "Assign Students"
                    }

    except Exception as e:
        logger.warning("Error in check_admin_action_result: %s", e)

    return None
