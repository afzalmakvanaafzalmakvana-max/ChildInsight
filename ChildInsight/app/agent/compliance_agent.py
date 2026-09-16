from datetime import datetime, timezone, timedelta
import logging
import re
import threading

logger = logging.getLogger('childinsight.compliance_agent')

# PRD §4 Ethical & Non-Diagnostic Clinical Language Blacklist (English)
FORBIDDEN_TERMS = [
    'adhd', 'autism', 'autistic', 'dyslexia', 'dyslexic', 'dyscalculia',
    'disorder', 'syndrome', 'deficit', 'abnormal', 'impaired', 'impairment',
    'pathology', 'pathological', 'iq', 'retarded', 'retardation', 'handicap',
    'handicapped', 'clinical', 'diagnosis', 'diagnostic', 'medical', 'mentally',
    'disease', 'illness', 'disability', 'disabled', 'asperger', 'neurodivergent'
]

# PRD §4 Ethical & Non-Diagnostic Clinical Language Blacklist (Hindi)
# Verified linguistically accurate equivalents for clinical, diagnostic, and medicalized terms.
# Any borderline terms or rationales are documented in memory.md.
FORBIDDEN_TERMS_HI = [
    'विकार',            # disorder
    'गड़बड़ी',          # dysfunction / disorder (in medical context)
    'सिंड्रोम',         # syndrome
    'संलक्षण',          # syndrome (formal Hindi)
    'निदान',            # diagnosis
    'नैदानिक',          # diagnostic / clinical
    'न्यूनता',           # deficit
    'कमी',              # deficit (e.g. ध्यान की कमी / अभाव)
    'असामान्य',         # abnormal
    'बाधित',            # impaired
    'क्षीणता',          # impairment
    'रोगविज्ञान',       # pathology
    'विकृति',           # pathological condition / malformation
    'आईक्यू',           # IQ
    'बुद्धिलब्धि',       # IQ / intelligence quotient
    'मंदबुद्धि',         # retarded / mentally deficient
    'मानसिक मंदता',     # mental retardation
    'विकलांग',          # handicapped / disabled
    'दिव्यांगता',        # disability (when used to label/diagnose)
    'अपंग',             # disabled / handicapped
    'अक्षमता',          # disability / incapacity
    'क्लिनिकल',         # clinical
    'चिकित्सीय',        # medical / clinical
    'ऑटिज्म',           # autism
    'आत्मकेंद्रित',      # autistic / self-absorbed in clinical sense
    'डिस्लेक्सिया',      # dyslexia
    'पठन विकार',        # dyslexia / reading disorder
    'एडीएचडी',          # ADHD
    'अतिसक्रियता',      # hyperactivity (ADHD context)
    'डिस्कैलकुलिया',     # dyscalculia
    'गणना विकार',       # dyscalculia / arithmetic disorder
    'एस्परगर',          # Asperger's
    'बीमारी',           # disease / illness
    'रोग',              # disease
    'मानसिक रोगी',      # mentally ill
    'मानसिक विकार',     # mental disorder
    'मानसिक रूप से',    # mentally (e.g. mentally weak/retarded)
    'न्यूरोडाइवर्जेंट'   # neurodivergent
]

_EN_PATTERN = re.compile(r'\b(' + '|'.join(re.escape(t) for t in FORBIDDEN_TERMS) + r')\b', re.IGNORECASE)
_HI_PATTERN = re.compile(r'(?:^|[^\w])(' + '|'.join(re.escape(t) for t in FORBIDDEN_TERMS_HI) + r')(?:$|[^\w])', re.IGNORECASE)

DEFAULT_FALLBACK_TEXT = "Practice recommended to reinforce core cognitive skills and support steady learning progression."
DEFAULT_FALLBACK_TEXT_HI = "मुख्य संज्ञानात्मक कौशलों को मजबूत करने और स्थिर सीखने की प्रगति का समर्थन करने के लिए अभ्यास की सिफारिश की जाती है।"

# Thread-safe in-memory rolling incident history for telemetry & dashboard
_LOCK = threading.Lock()
_INCIDENT_HISTORY = []
MAX_HISTORY_ITEMS = 500


def check_text(text: str):
    """
    Scans a string against both the English and Hindi diagnostic/clinical language blacklists.
    Returns (is_safe: bool, reason: str | None).
    """
    if not text or not isinstance(text, str):
        return True, None

    # Check English clinical blacklist
    match_en = _EN_PATTERN.search(text)
    if match_en:
        matched_term = match_en.group(1).lower()
        return False, f"Matched forbidden clinical term: '{matched_term}'"

    # Check Hindi clinical blacklist
    match_hi = _HI_PATTERN.search(text)
    if match_hi:
        matched_term = match_hi.group(1).strip()
        return False, f"Matched forbidden Hindi clinical term: '{matched_term}'"

    return True, None


def check_activity_translations(translations: dict) -> tuple[bool, str | None]:
    """
    Validates a translations dictionary (e.g. {'hi': {'title': ..., 'description': ..., 'questions': [...]}})
    against the clinical language blacklists.
    Returns (is_safe: bool, reason: str | None).
    """
    if not translations or not isinstance(translations, dict):
        return True, None

    for lang_code, lang_data in translations.items():
        if not isinstance(lang_data, dict):
            continue

        for field in ('title', 'description'):
            val = lang_data.get(field)
            if val:
                is_safe, reason = check_text(val)
                if not is_safe:
                    return False, f"In translation [{lang_code}] {field}: {reason}"

        questions = lang_data.get('questions', [])
        if isinstance(questions, list):
            for idx, q in enumerate(questions):
                if not isinstance(q, dict):
                    continue
                for q_field in ('question_text', 'correct_answer', 'hint'):
                    q_val = q.get(q_field)
                    if q_val:
                        is_safe, reason = check_text(q_val)
                        if not is_safe:
                            return False, f"In translation [{lang_code}] question #{idx+1} {q_field}: {reason}"
                for opt in q.get('options', []):
                    if opt:
                        is_safe, reason = check_text(str(opt))
                        if not is_safe:
                            return False, f"In translation [{lang_code}] question #{idx+1} option: {reason}"

    return True, None


def enforce_compliance(text: str, context: dict = None, fallback_text: str = None) -> str:
    """
    Enforces compliance on a message, recommendation reason, or report text.
    If clean: returns the original text.
    If a violation is found: logs the incident with full context to the server log,
    records incident telemetry, and returns a safe generic educational fallback
    (adapting to Hindi when text contains Devanagari characters or lang is Hindi).
    """
    is_safe, reason = check_text(text)
    if is_safe:
        return text

    ctx = context or {}
    now = datetime.now(timezone.utc)
    source = ctx.get('source', 'unknown')
    child_id = ctx.get('child_id')
    user_id = ctx.get('user_id')

    # Detect if content is primarily Hindi / Devanagari
    has_devanagari = any('\u0900' <= ch <= '\u097F' for ch in (text or ''))
    default_fb = DEFAULT_FALLBACK_TEXT_HI if (has_devanagari or ctx.get('lang') == 'hi') else DEFAULT_FALLBACK_TEXT
    selected_fallback = fallback_text or ctx.get('fallback_text') or default_fb

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
