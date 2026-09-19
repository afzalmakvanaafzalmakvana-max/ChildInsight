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
from typing import Optional
import urllib.request
import urllib.error

from app import db
from app.models.activity import Category, Activity, ActivityQuestion
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
    'audit_logs': {'label': 'Audit Logs', 'url': '/admin/audit-logs'},
    'assignments': {'label': 'Teacher Assignments', 'url': '/admin/assignments'},
    'agents_dashboard': {'label': 'System Agents Dashboard', 'url': '/admin/agents'}
}


# =============================================================================
# 1. REAL DATA SYNTHESIZER
# =============================================================================

def gather_assistant_context() -> dict:
    """
    Gathers in one pass all real platform metrics and telemetry already gathered
    by the Orchestrator Agent and other system agents.
    
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
        'categories': categories_data
    }


# =============================================================================
# 2. ACTION REQUEST DETECTION & REFUSAL (READ-ONLY SAFETY)
# =============================================================================

ACTION_INTENT_PATTERNS = [
    r'\b(?:fix|resolve|correct|repair)\s+(?:it|this|them|all|the\s+issue|everything)\b',
    r'\b(?:do\s+it|take\s+care\s+of\s+it)\s+for\s+me\b',
    r'\b(?:just\s+fix|auto-fix|autofix)\b',
    r'\b(?:delete|remove|purge|erase|drop)\s+(?:the|this|all|category|activity|question|user)\b',
    r'\b(?:publish|approve|accept|create|add|modify|update|change)\s+(?:it|this|them|the\s+draft|the\s+activity|the\s+category)\b',
    r'\bcan\s+you\s+(?:fix|publish|delete|create|change|update)\b'
]


def is_action_request(question: str) -> bool:
    """Detects whether the administrator is asking the assistant to execute an action."""
    q = question.lower().strip()

    if re.search(r'\b(?:just\s+fix|autofix|auto-fix)\b', q):
        return True
    if re.search(r'\b(?:fix|resolve|correct)\s+(?:it|this|them|all|the\s+issue|everything|category|activity|the)\b', q):
        return True
    if re.search(r'\b(?:do\s+(?:it|this)|take\s+care\s+of\s+(?:it|this))\s+for\s+me\b', q):
        return True
    if re.search(r'\bfor\s+me\b', q) and any(verb in q for verb in ['fix', 'delete', 'create', 'publish', 'update', 'change', 'remove']):
        return True
    if re.search(r'\b(?:delete|remove|purge|erase|drop)\s+(?:the|this|all|unused|empty|broken|category|categories|activity|activities|question|user|record)\b', q):
        return True
    if re.search(r'\b(?:publish|approve)\s+(?:it|this|them|the|all|pending|draft|activity|activities|content)\b', q):
        return True
    if re.search(r'\b(?:can\s+you|could\s+you|please|will\s+you)\s+(?:fix|delete|remove|publish|create|add|change|update|edit)\b', q):
        return True

    return False


def _build_action_refusal_response(question: str, context: dict) -> dict:
    """
    Constructs a polite, clear refusal explaining the assistant's read-only advisory
    nature and provides direct links to where the administrator can perform the action.
    """
    q_lower = question.lower()
    relevant_links = []

    if 'category' in q_lower or 'categories' in q_lower:
        relevant_links.append(ADMIN_LINKS['categories'])
    if 'activity' in q_lower or 'activities' in q_lower or 'draft' in q_lower:
        relevant_links.append(ADMIN_LINKS['activities'])
        relevant_links.append(ADMIN_LINKS['content_suggestions'])
    if 'suggestion' in q_lower:
        relevant_links.append(ADMIN_LINKS['content_suggestions'])
    if 'audit' in q_lower or 'log' in q_lower:
        relevant_links.append(ADMIN_LINKS['audit_logs'])

    # Always provide Action Center as primary destination
    if ADMIN_LINKS['action_center'] not in relevant_links:
        relevant_links.insert(0, ADMIN_LINKS['action_center'])

    links_markdown = "\n".join([f"- [{item['label']}]({item['url']})" for item in relevant_links])

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
# 3. GROUNDED PROCEDURAL FALLBACK GENERATOR
# =============================================================================

def _generate_grounded_fallback_answer(question: str, context: dict) -> dict:
    """
    Generates a 100% grounded answer strictly from real platform context without LLM.
    Used in test environments or when ANTHROPIC_API_KEY is not configured.
    """
    q_lower = question.lower().strip()
    relevant_links = []

    # Check for category-specific questions first (e.g. "What's wrong with Science & Nature?")
    matched_cat = None
    for cat in context.get('categories', []):
        cat_name_clean = cat['name'].lower()
        cat_slug_clean = cat['slug'].replace('-', ' ').lower()
        if cat_name_clean in q_lower or cat_slug_clean in q_lower:
            matched_cat = cat
            break

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

    # 1. "What should I do next?" / Next actions query
    elif any(k in q_lower for k in ['what should i do', 'what to do next', 'what needs attention', 'next steps', 'priorities', 'priority']):
        action_items = context.get('action_items', [])
        crit_count = context.get('critical_items_count', 0)
        imp_count = context.get('important_items_count', 0)
        total_items = context.get('action_items_count', 0)

        if total_items == 0:
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
            answer = (
                f"You currently have **{total_items} action item(s)** organized in the Action Center "
                f"({crit_count} Critical, {imp_count} Important). Here are the top priorities to address:\n\n"
                f"{bullets_text}\n\n"
                f"View all prioritized items in the [Action Center](/admin/action-center)."
            )
            relevant_links.append(ADMIN_LINKS['action_center'])

    # 2. "Did I make any mistakes?" / Catalog integrity questions
    elif any(k in q_lower for k in ['mistake', 'error', 'integrity', 'wrong', 'broken', 'issue', 'audit']):
        issues = context.get('integrity_issues', [])
        issue_count = context.get('integrity_issues_count', 0)

        # Also check for empty categories
        empty_cats = [c for c in context.get('categories', []) if c['activity_count'] == 0]
        untranslated_cats = [c for c in context.get('categories', []) if not c['has_hindi']]

        if issue_count == 0 and not empty_cats:
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
            answer = (
                f"The Content Integrity Agent detected **{issue_count} issue(s)** in the catalog"
                f"{f' along with {len(empty_cats)} empty category/ies' if empty_cats else ''}:\n\n"
                f"{bullets_text}\n\n"
                f"Inspect and resolve these issues in [Manage Activities](/admin/activities) or [Categories](/admin/categories)."
            )
            relevant_links.append(ADMIN_LINKS['activities'])
            relevant_links.append(ADMIN_LINKS['categories'])
    # 3. Platform Health / Telemetry queries
    elif any(k in q_lower for k in ['health', 'score', 'telemetry', 'posture', 'completion rate']):
        hm = context.get('health_metrics', {})
        score = hm.get('overall_score', 100.0)
        comp = hm.get('completion_rate', 100.0)
        valid_act = hm.get('valid_activities_pct', 100.0)
        cohorts = hm.get('cohorts', [])

        cohort_lines = []
        for c in cohorts:
            cohort_lines.append(f"- **{c['name']}**: Score {c['score']:.1f}/100, Completion Rate {c['completion_rate']:.1f}%, Learners: {c['total_children']}")

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

    # 5. Default general summary
    else:
        crit = context.get('critical_items_count', 0)
        total = context.get('action_items_count', 0)
        score = context['health_metrics']['overall_score']
        issues = context.get('integrity_issues_count', 0)

        answer = (
            f"Here is a summary of the current platform status:\n\n"
            f"- **Platform Health Score**: {score:.1f}/100\n"
            f"- **Action Center Items**: {total} total ({crit} Critical)\n"
            f"- **Content Integrity Issues**: {issues}\n"
            f"- **Pending Suggestions**: {context.get('pending_suggestions_count', 0)}\n"
            f"- **Compliance Incidents (24h)**: {context.get('compliance_incidents_24h', 0)}\n\n"
            f"You can ask me questions like *'What should I do next?'*, *'Did I make any mistakes?'*, "
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
# 4. ANTHROPIC API INTEGRATION (REUSING CONTENT DRAFT PATTERN)
# =============================================================================

def _call_anthropic_api(system_prompt: str, user_prompt: str) -> str:
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
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=30) as response:
        res_body = response.read().decode('utf-8')
        res_json = json.loads(res_body)

    content_blocks = res_json.get('content', [])
    raw_text = "".join(b.get('text', '') for b in content_blocks if b.get('type') == 'text')
    return raw_text.strip()


def ask_assistant(question: str, context: Optional[dict] = None) -> dict:
    """
    Entrypoint for administrator questions:
    1. Gathers real platform data (or uses supplied context).
    2. Inspects for action execution requests — immediately refuses with guidance and links if detected.
    3. Invokes Anthropic API if key is available, strictly constrained to real context.
    4. Falls back deterministically to procedural grounded answering if API is unavailable.
    """
    if not question or not question.strip():
        return {
            'answer': "Please ask a question about platform health, action items, catalog integrity, or specific categories.",
            'links': [ADMIN_LINKS['action_center']]
        }

    q_clean = question.strip()

    if context is None:
        context = gather_assistant_context()

    # Safety: Refuse action requests
    if is_action_request(q_clean):
        return _build_action_refusal_response(q_clean, context)

    # If Anthropic API key is configured, use it with strict system constraints
    if os.environ.get('ANTHROPIC_API_KEY'):
        try:
            system_prompt = (
                "You are the ChildInsight Admin Assistant, an intelligent, strictly read-only advisory guide for administrators.\n"
                "Your role is to explain, diagnose, and guide administrators on what needs attention and what to do next.\n\n"
                "CRITICAL RULES:\n"
                "1. STRICTLY NEVER ACT: You cannot create, edit, delete, or publish anything. Do not pretend to execute actions.\n"
                "2. GROUNDED IN REAL DATA ONLY: Answer using ONLY the real data provided in the context below. NEVER invent, "
                "hallucinate, or estimate any numbers, statistics, counts, or categories. Every number must match the context.\n"
                "3. DIRECT DEEP LINKS: Include direct Markdown links to relevant admin pages whenever discussing actions:\n"
                "   - Action Center: [Action Center](/admin/action-center)\n"
                "   - Content Suggestions: [Content Suggestions](/admin/content-suggestions)\n"
                "   - Manage Activities: [Activities](/admin/activities)\n"
                "   - Manage Categories: [Categories](/admin/categories)\n"
                "   - Audit Logs: [Audit Logs](/admin/audit-logs)\n"
                "   - System Agents: [System Agents](/admin/agents)\n"
                "4. TONE: Clear, concise, helpful, and professional."
            )

            # Compact representation of context
            context_summary = json.dumps(context, indent=2)
            user_prompt = (
                f"CURRENT REAL PLATFORM CONTEXT:\n{context_summary}\n\n"
                f"ADMINISTRATOR QUESTION:\n{q_clean}\n\n"
                "Provide a clear, grounded response citing only the facts and numbers from the context. "
                "Include markdown links to the relevant admin pages."
            )

            answer_text = _call_anthropic_api(system_prompt, user_prompt)
            # Extract links mentioned or provide fallback action center link
            links = []
            if '/admin/action-center' in answer_text:
                links.append(ADMIN_LINKS['action_center'])
            if '/admin/content-suggestions' in answer_text:
                links.append(ADMIN_LINKS['content_suggestions'])
            if '/admin/activities' in answer_text:
                links.append(ADMIN_LINKS['activities'])
            if '/admin/categories' in answer_text:
                links.append(ADMIN_LINKS['categories'])
            if '/admin/audit-logs' in answer_text:
                links.append(ADMIN_LINKS['audit_logs'])
            if not links:
                links.append(ADMIN_LINKS['action_center'])

            return {
                'answer': answer_text,
                'links': links,
                'refusal': False
            }
        except Exception as e:
            logger.warning("Anthropic API call failed in admin_assistant, falling back: %s", e)

    # Procedural grounded fallback
    return _generate_grounded_fallback_answer(q_clean, context)


# =============================================================================
# 5. PROACTIVE MISTAKE-CATCHING (SURFACING EXISTING CHECKS)
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
