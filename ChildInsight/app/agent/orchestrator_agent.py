"""
Orchestrator Agent (app/agent/orchestrator_agent.py)

A strictly read-only coordinator agent that reads the outputs of existing internal
agents (Compliance, Content Integrity, Platform Health, Content Suggestion, and
Content Draft) in one pass, deduplicates and groups related issues across age bands,
assigns objective priority tiers (Critical, Important, Minor) grounded in real metrics,
and produces a consolidated, prioritized action list for administrators.

IMPORTANT ARCHITECTURAL CONSTRAINTS:
1. STRICTLY READ-ONLY: Never creates, modifies, publishes, or deletes content,
   activities, questions, categories, suggestions, or user records.
2. HONEST, NON-AGI FRAMING: A deterministic rule-based coordinator and synthesizer;
   it organizes and explains, it never acts on its own.
3. GROUNDED SUMMARIES: All numbers in summary strings trace back to real database
   entities and computed agent metrics.
"""

from datetime import datetime, timezone
import re
from typing import Optional

from app import db
from app.models.content_suggestion import ContentSuggestion
from app.models.activity import Category, Activity, ActivityQuestion
from app.agent import (
    compliance_agent,
    content_integrity_agent,
    health_agent
)

# In-memory store for session/server-level dismissals (cleans view without DB mutation)
_DISMISSED_KEYS: set[str] = set()


# Priority Tier Constants
TIER_CRITICAL = 'Critical'
TIER_IMPORTANT = 'Important'
TIER_MINOR = 'Minor'

TIER_ORDER = {
    TIER_CRITICAL: 1,
    TIER_IMPORTANT: 2,
    TIER_MINOR: 3
}


def _extract_numbers_from_text(text: str) -> list[float]:
    """Extracts all numbers from text for traceable synthesis."""
    if not text:
        return []
    return [float(x) for x in re.findall(r'\b\d+(?:\.\d+)?\b', text)]


def _extract_affected_children_from_reason(reason: str) -> int:
    """
    Extracts the affected children count from a content suggestion reason string.
    Patterns commonly look like '14 children aged 9-12' or '2 Hindi-preferring learners'.
    """
    if not reason:
        return 0
    # Match patterns like "X children" or "X learners" or "X registered learners"
    match = re.search(r'(\d+)\s+(?:children|learners|registered\s+learners|Hindi-preferring\s+learners)', reason, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return 0


def _format_age_bands_display(age_bands: list[str]) -> str:
    """Formats a list of age bands into a clean string e.g. 'affects ages 4-6, 9-12, 12-14'."""
    if not age_bands:
        return 'all age groups'
    # Deduplicate and sort bands by numerical start
    clean_bands = []
    seen = set()
    for b in age_bands:
        b_str = str(b).strip()
        if b_str and b_str not in seen:
            seen.add(b_str)
            clean_bands.append(b_str)

    def sort_key(b):
        m = re.search(r'(\d+)', b)
        return int(m.group(1)) if m else 99

    clean_bands.sort(key=sort_key)
    return f"affects ages {', '.join(clean_bands)}"


def get_action_items(dismissed_keys: Optional[set[str]] = None) -> list[dict]:
    """
    Pulls in one pass:
    - All pending content suggestions (including translation_gap type)
    - All content integrity agent audit issues
    - The latest platform health metrics and per-age-band breakdown
    - Recent compliance incident telemetry

    Deduplicates and groups related items (e.g. multiple warnings for the same
    category across different age bands), assigns priority tiers, and produces
    a sorted action list.
    """
    active_dismissals = set(_DISMISSED_KEYS)
    if dismissed_keys:
        active_dismissals.update(dismissed_keys)

    action_items = []

    # =========================================================================
    # 1. GROUP & DEDUPLICATE PENDING CONTENT SUGGESTIONS
    # =========================================================================
    try:
        pending_suggestions = ContentSuggestion.query.filter_by(
            status=ContentSuggestion.STATUS_PENDING
        ).all()
    except Exception:
        pending_suggestions = []

    # Group suggestions by category (or topic for new categories)
    suggestion_groups = {}
    for sug in pending_suggestions:
        if sug.category_id:
            group_key = f"suggestion_cat_{sug.category_id}"
            cat_name = sug.category.name if sug.category else f"Category #{sug.category_id}"
        else:
            topic = sug.suggested_title or sug.suggestion_type
            slug = re.sub(r'[^a-zA-Z0-9]+', '_', topic).strip('_').lower()
            group_key = f"suggestion_topic_{slug}"
            cat_name = sug.suggested_title or "New Learning Domain"

        if group_key not in suggestion_groups:
            suggestion_groups[group_key] = {
                'group_key': group_key,
                'category_id': sug.category_id,
                'category_name': cat_name,
                'suggestions': [],
                'age_bands': set(),
                'suggestion_types': set(),
                'max_priority_score': 0.0,
                'max_persistence': 1,
                'total_affected_children': 0,
                'has_translation_gap': False
            }

        group = suggestion_groups[group_key]
        group['suggestions'].append(sug)
        if sug.age_band:
            group['age_bands'].add(sug.age_band)
        group['suggestion_types'].add(sug.suggestion_type)
        if sug.suggestion_type == ContentSuggestion.TYPE_TRANSLATION_GAP:
            group['has_translation_gap'] = True

        score = float(sug.priority_score or 0.0)
        if score > group['max_priority_score']:
            group['max_priority_score'] = score

        persistence = int(sug.persistence_count or 1)
        if persistence > group['max_persistence']:
            group['max_persistence'] = persistence

        affected = _extract_affected_children_from_reason(sug.reason)
        # Sum or take max of affected children across suggestions
        group['total_affected_children'] = max(group['total_affected_children'], affected)

    for group_key, group in suggestion_groups.items():
        age_bands_list = list(group['age_bands'])
        age_bands_display = _format_age_bands_display(age_bands_list)
        sug_count = len(group['suggestions'])
        cat_name = group['category_name']
        score = group['max_priority_score']
        persistence = group['max_persistence']
        affected = group['total_affected_children']

        # Determine Priority Tier based on real numbers
        if score >= 25.0 or affected >= 10 or persistence >= 3:
            tier = TIER_CRITICAL
        elif score >= 10.0 or affected > 0 or group['has_translation_gap']:
            tier = TIER_IMPORTANT
        else:
            tier = TIER_MINOR

        # Construct grounded plain-language summary
        primary_sug = group['suggestions'][0]
        types_desc = ', '.join(t.replace('_', ' ') for t in sorted(group['suggestion_types']))

        if group['has_translation_gap']:
            summary = (
                f"Translation accessibility gap in {cat_name} ({age_bands_display}): "
                f"{affected} learner(s) need translated activities (urgency score {score}, "
                f"persisting for {persistence} run(s)). Adding Hindi content unlocks learning."
            )
            action_url = "/admin/content-suggestions"
            action_label = "Review Translation Suggestions"
        elif affected > 0:
            summary = (
                f"{affected} child(ren) ({age_bands_display}) affected by curriculum gap in {cat_name} "
                f"(urgency score {score}, persisted {persistence} run(s)). Addressing this prevents learning stalls."
            )
            action_url = f"/admin/activities/ai-draft/generate?category_id={group['category_id']}" if group['category_id'] else "/admin/content-suggestions"
            action_label = "Draft Activity with AI" if group['category_id'] else "Review Suggestions"
        else:
            summary = (
                f"Catalog expansion opportunity for {cat_name} ({age_bands_display}): "
                f"{sug_count} suggestion(s) ({types_desc}) with priority score {score}."
            )
            action_url = "/admin/content-suggestions"
            action_label = "Review Suggestions"

        action_items.append({
            'key': group_key,
            'source': 'Content Suggestions',
            'source_badge': 'badge-warning',
            'title': f"Content Opportunity: {cat_name}",
            'subtitle': age_bands_display,
            'priority_tier': tier,
            'priority_rank': TIER_ORDER[tier],
            'priority_score': score,
            'summary': summary,
            'action_url': action_url,
            'action_label': action_label,
            'meta': {
                'category_id': group['category_id'],
                'category_name': cat_name,
                'age_bands': age_bands_list,
                'suggestion_ids': [s.id for s in group['suggestions']],
                'affected_children': affected,
                'persistence_count': persistence,
                'priority_score': score
            }
        })

    # =========================================================================
    # 2. GROUP & DEDUPLICATE CONTENT INTEGRITY ISSUES
    # =========================================================================
    try:
        integrity_issues = content_integrity_agent.run_audit()
    except Exception:
        integrity_issues = []

    # Group issues by affected entity (activity or category)
    integrity_groups = {}
    for issue in integrity_issues:
        rec_type = issue.get('record_type', 'unknown')
        rec_id = issue.get('record_id', 0)
        group_key = f"integrity_{rec_type}_{rec_id}"

        if group_key not in integrity_groups:
            integrity_groups[group_key] = {
                'group_key': group_key,
                'record_type': rec_type,
                'record_id': rec_id,
                'affected_record': issue.get('affected_record', f"{rec_type} #{rec_id}"),
                'issues': [],
                'severities': []
            }

        group = integrity_groups[group_key]
        group['issues'].append(issue)
        group['severities'].append(issue.get('severity', 'medium'))

    for group_key, group in integrity_groups.items():
        severities = group['severities']
        if 'high' in severities:
            tier = TIER_CRITICAL
        elif 'medium' in severities:
            tier = TIER_IMPORTANT
        else:
            tier = TIER_MINOR

        issue_count = len(group['issues'])
        first_issue = group['issues'][0]
        affected_record = group['affected_record']
        descriptions = [i.get('description', '') for i in group['issues']]
        combined_desc = '; '.join(descriptions[:2])

        # Deep link target
        rec_type = group['record_type']
        rec_id = group['record_id']
        if rec_type == 'activity':
            action_url = f"/admin/activities/{rec_id}/edit"
            action_label = "Edit Activity"
        elif rec_type == 'question':
            action_url = "/admin/activities"
            action_label = "Inspect Questions"
        elif rec_type == 'category':
            action_url = "/admin/categories"
            action_label = "Manage Categories"
        else:
            action_url = "/admin/agents"
            action_label = "View Audit"

        summary = (
            f"Catalog integrity anomaly on {affected_record}: {combined_desc} "
            f"Fix: {first_issue.get('suggested_fix', 'Inspect and resolve in admin console.')}"
        )

        action_items.append({
            'key': group_key,
            'source': 'Content Integrity',
            'source_badge': 'badge-danger',
            'title': f"Catalog Anomaly: {affected_record}",
            'subtitle': f"{issue_count} integrity issue(s) detected",
            'priority_tier': tier,
            'priority_rank': TIER_ORDER[tier],
            'priority_score': 30.0 if tier == TIER_CRITICAL else (15.0 if tier == TIER_IMPORTANT else 5.0),
            'summary': summary,
            'action_url': action_url,
            'action_label': action_label,
            'meta': {
                'record_type': rec_type,
                'record_id': rec_id,
                'issues_count': issue_count,
                'severities': severities
            }
        })

    # =========================================================================
    # 3. PLATFORM & COHORT HEALTH ALERTS
    # =========================================================================
    try:
        health_metrics = health_agent.get_latest_health()
    except Exception:
        health_metrics = {}

    overall_score = float(health_metrics.get('score', 100.0))
    if overall_score < 60.0:
        action_items.append({
            'key': 'health_overall_critical',
            'source': 'Platform Health',
            'source_badge': 'badge-danger',
            'title': "Platform Health Alert: Low System Posture",
            'subtitle': f"Overall Score: {overall_score}/100",
            'priority_tier': TIER_CRITICAL,
            'priority_rank': TIER_ORDER[TIER_CRITICAL],
            'priority_score': 35.0,
            'summary': (
                f"Platform health score has dropped to {overall_score}/100. "
                f"Session completion rate is {health_metrics.get('completion_rate', 0)}% "
                f"and valid activity content is {health_metrics.get('valid_activities_pct', 0)}%. "
                f"Immediate administrative intervention is recommended."
            ),
            'action_url': "/admin/agents",
            'action_label': "Review System Telemetry",
            'meta': {'score': overall_score}
        })

    # Per-age-band health checks
    for band in health_metrics.get('age_band_breakdown', []):
        band_score = float(band.get('score', 100.0))
        band_completion = float(band.get('completion_rate', 100.0))
        band_adequacy = float(band.get('content_adequacy', 100.0))
        band_children = int(band.get('total_children', 0))
        band_sessions = int(band.get('total_sessions', 0))
        band_label = band.get('age_band', '')
        band_name = band.get('name', f"Ages {band_label}")

        # Alert if score < 70 or completion < 50% with enrolled learners
        if band_children > 0 and (band_score < 70.0 or band_completion < 50.0 or band_adequacy < 50.0):
            tier = TIER_CRITICAL if band_score < 50.0 else TIER_IMPORTANT
            group_key = f"health_cohort_{band_label}"

            summary = (
                f"{band_name} health score is {band_score}/100 ({band_children} enrolled children). "
                f"Completion rate is {band_completion}% across {band_sessions} sessions with "
                f"{band_adequacy}% content adequacy. Reviewing difficulty and content for this age group is recommended."
            )

            action_items.append({
                'key': group_key,
                'source': 'Cohort Health',
                'source_badge': 'badge-primary',
                'title': f"Cohort Health Concern: Ages {band_label}",
                'subtitle': f"{band_name} (Score: {band_score}/100)",
                'priority_tier': tier,
                'priority_rank': TIER_ORDER[tier],
                'priority_score': 20.0 if tier == TIER_CRITICAL else 12.0,
                'summary': summary,
                'action_url': "/admin/agents",
                'action_label': "Inspect Cohort Table",
                'meta': {
                    'age_band': band_label,
                    'score': band_score,
                    'completion_rate': band_completion,
                    'content_adequacy': band_adequacy,
                    'total_children': band_children
                }
            })

    # =========================================================================
    # 4. COMPLIANCE INCIDENTS TELEMETRY
    # =========================================================================
    try:
        incidents_count = compliance_agent.get_recent_incident_count(since_hours=24)
    except Exception:
        incidents_count = 0

    if incidents_count > 0:
        summary = (
            f"{incidents_count} non-compliant clinical/diagnostic term(s) were intercepted and "
            f"substituted in the past 24 hours. Reviewing recommendation and drafting prompts "
            f"ensures continued adherence to PRD §4 non-diagnostic standards."
        )
        action_items.append({
            'key': 'compliance_incidents_alert',
            'source': 'Safety & Compliance',
            'source_badge': 'badge-danger',
            'title': "Compliance Alert: Intercepted Diagnostic Terms",
            'subtitle': f"{incidents_count} incident(s) in last 24h",
            'priority_tier': TIER_CRITICAL,
            'priority_rank': TIER_ORDER[TIER_CRITICAL],
            'priority_score': 25.0 + float(incidents_count * 2.0),
            'summary': summary,
            'action_url': "/admin/agents",
            'action_label': "View Compliance Log",
            'meta': {'incidents_count': incidents_count}
        })

    # =========================================================================
    # 5. SORTING & DISMISSAL FILTERING
    # =========================================================================
    # Sort deterministically by:
    # 1. priority_rank (1=Critical, 2=Important, 3=Minor)
    # 2. priority_score descending
    # 3. key string
    action_items.sort(key=lambda item: (item['priority_rank'], -item['priority_score'], item['key']))

    # Attach is_dismissed flag and return filtered active list
    for item in action_items:
        item['is_dismissed'] = item['key'] in active_dismissals

    return action_items


def get_active_action_items(dismissed_keys: Optional[set[str]] = None) -> list[dict]:
    """Returns only active (non-dismissed) action items."""
    all_items = get_action_items(dismissed_keys=dismissed_keys)
    return [i for i in all_items if not i['is_dismissed']]


def dismiss_action_item(key: str) -> None:
    """Marks an action item as dismissed in-memory (does not mutate database)."""
    if key:
        _DISMISSED_KEYS.add(str(key).strip())


def restore_action_item(key: str) -> None:
    """Restores a previously dismissed action item in-memory."""
    if key and key in _DISMISSED_KEYS:
        _DISMISSED_KEYS.remove(key)


def clear_dismissed_items() -> None:
    """Clears all in-memory dismissals."""
    _DISMISSED_KEYS.clear()


def get_dismissed_count(session_dismissals: Optional[set[str]] = None) -> int:
    """Returns total count of dismissed item keys."""
    keys = set(_DISMISSED_KEYS)
    if session_dismissals:
        keys.update(session_dismissals)
    return len(keys)
