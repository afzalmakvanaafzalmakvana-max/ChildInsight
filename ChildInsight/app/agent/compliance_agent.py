from datetime import datetime, timezone, timedelta
import logging
import re
import threading

logger = logging.getLogger('childinsight.compliance_agent')

# PRD §4 Ethical & Non-Diagnostic Clinical Language Blacklist
FORBIDDEN_TERMS = [
    'adhd', 'autism', 'autistic', 'dyslexia', 'dyslexic', 'dyscalculia',
    'disorder', 'syndrome', 'deficit', 'abnormal', 'impaired', 'impairment',
    'pathology', 'pathological', 'iq', 'retarded', 'retardation', 'handicap',
    'handicapped', 'clinical', 'diagnosis', 'diagnostic', 'medical', 'mentally',
    'disease', 'illness', 'disability', 'disabled', 'asperger', 'neurodivergent'
]

_PATTERN = re.compile(r'\b(' + '|'.join(re.escape(t) for t in FORBIDDEN_TERMS) + r')\b', re.IGNORECASE)

DEFAULT_FALLBACK_TEXT = "Practice recommended to reinforce core cognitive skills and support steady learning progression."

# Thread-safe in-memory rolling incident history for telemetry & dashboard
_LOCK = threading.Lock()
_INCIDENT_HISTORY = []
MAX_HISTORY_ITEMS = 500


def check_text(text: str):
    """
    Scans a string against the diagnostic/clinical language blacklist.
    Returns (is_safe: bool, reason: str | None).
    """
    if not text or not isinstance(text, str):
        return True, None

    match = _PATTERN.search(text)
    if match:
        matched_term = match.group(0).lower()
        return False, f"Matched forbidden clinical term: '{matched_term}'"
    return True, None


def enforce_compliance(text: str, context: dict = None, fallback_text: str = None) -> str:
    """
    Enforces compliance on a message, recommendation reason, or report text.
    If clean: returns the original text.
    If a violation is found: logs the incident with full context to the server log,
    records incident telemetry, and returns a safe generic educational fallback.
    """
    is_safe, reason = check_text(text)
    if is_safe:
        return text

    ctx = context or {}
    now = datetime.now(timezone.utc)
    source = ctx.get('source', 'unknown')
    child_id = ctx.get('child_id')
    user_id = ctx.get('user_id')
    selected_fallback = fallback_text or ctx.get('fallback_text') or DEFAULT_FALLBACK_TEXT

    # Log full context incident to server log
    log_msg = (
        f"[COMPLIANCE_INCIDENT] Rule='{reason}' Source='{source}' "
        f"ChildID={child_id} UserID={user_id} Timestamp='{now.isoformat()}' "
        f"BlockedText='{text}' FallbackText='{selected_fallback}'"
    )
    logger.warning(log_msg)

    # Record telemetry for health score and dashboard (omitting raw text for privacy)
    with _LOCK:
        incident_record = {
            'timestamp': now,
            'rule_matched': reason,
            'source': source,
            'child_id': child_id,
            'user_id': user_id,
            'action': 'blocked_and_substituted'
        }
        _INCIDENT_HISTORY.append(incident_record)
        if len(_INCIDENT_HISTORY) > MAX_HISTORY_ITEMS:
            _INCIDENT_HISTORY.pop(0)

    return selected_fallback


def get_recent_incident_count(since_hours: int = 24) -> int:
    """Returns the count of compliance incidents recorded within the given window."""
    threshold = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    with _LOCK:
        return sum(1 for inc in _INCIDENT_HISTORY if inc['timestamp'] >= threshold)


def get_recent_incidents_summary(limit: int = 20) -> list:
    """
    Returns sanitized incident metadata (counts, rule matched, timestamp)
    WITHOUT exposing the raw blocked text to preserve learner privacy.
    """
    with _LOCK:
        recent = sorted(_INCIDENT_HISTORY, key=lambda x: x['timestamp'], reverse=True)[:limit]
        return [
            {
                'timestamp': inc['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC'),
                'rule_matched': inc['rule_matched'],
                'source': inc['source'],
                'child_id': inc['child_id'],
                'user_id': inc['user_id'],
                'action': inc['action']
            }
            for inc in recent
        ]


def reset_incident_history():
    """Resets in-memory incident history (primarily for test isolation)."""
    with _LOCK:
        _INCIDENT_HISTORY.clear()
