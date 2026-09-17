from app import db
from app.models.activity import Activity, Category, ActivityQuestion


def run_audit() -> list:
    """
    Audits the educational content catalog for integrity anomalies:
    1. Activities with zero questions
    2. Categories with zero activities
    3. Orphaned questions (referencing non-existent activities)
    4. Activities with invalid difficulty or age-range values
    5. Duplicate question text within the same activity

    Returns a list of structured issue dictionaries.
    """
    issues = []

    # 1. Categories with zero activities
    categories = Category.query.all()
    for cat in categories:
        act_count = cat.activities.count() if hasattr(cat.activities, 'count') else len(cat.activities)
        if act_count == 0:
            issues.append({
                'issue_type': 'empty_category',
                'severity': 'medium',
                'affected_record': f"Category: {cat.name} (ID: {cat.id})",
                'record_type': 'category',
                'record_id': cat.id,
                'description': f"Category '{cat.name}' has 0 activities associated with it.",
                'suggested_fix': f"Create at least one activity under '{cat.name}' or remove the unused category."
            })

    # 2. Activities checks: zero questions, invalid difficulty/age bounds, duplicate questions
    valid_difficulties = set(Activity.DIFFICULTIES)
    activities = Activity.query.all()
    all_activity_ids = {a.id for a in activities}

    for act in activities:
        # Check zero questions
        q_count = act.questions.count() if hasattr(act.questions, 'count') else len(act.questions)
        if q_count == 0:
            issues.append({
                'issue_type': 'zero_questions',
                'severity': 'high',
                'affected_record': f"Activity: {act.title} (ID: {act.id})",
                'record_type': 'activity',
                'record_id': act.id,
                'description': f"Activity '{act.title}' has 0 questions and cannot be played by children.",
                'suggested_fix': "Add at least 3-5 questions or set this activity to inactive."
            })

        # Check invalid difficulty
        if act.difficulty not in valid_difficulties:
            issues.append({
                'issue_type': 'invalid_bounds',
                'severity': 'high',
                'affected_record': f"Activity: {act.title} (ID: {act.id})",
                'record_type': 'activity',
                'record_id': act.id,
                'description': f"Invalid difficulty '{act.difficulty}'. Must be one of: {', '.join(Activity.DIFFICULTIES)}.",
                'suggested_fix': "Update the activity's difficulty to a valid standard level."
            })

        # Check invalid age range
        min_age = getattr(act, 'min_age', None)
        max_age = getattr(act, 'max_age', None)
        if min_age is None or max_age is None or min_age < 3 or max_age > 18 or min_age > max_age:
            issues.append({
                'issue_type': 'invalid_bounds',
                'severity': 'medium',
                'affected_record': f"Activity: {act.title} (ID: {act.id})",
                'record_type': 'activity',
                'record_id': act.id,
                'description': f"Invalid age range [{min_age} - {max_age}]. Min age must be >= 3, max age <= 18, and min <= max.",
                'suggested_fix': "Adjust the min_age and max_age parameters in the activity editor."
            })

        # Check duplicate question text within the same activity
        seen_texts = set()
        act_questions = act.questions.all() if hasattr(act.questions, 'all') else act.questions
        for q in act_questions:
            cleaned = (q.question_text or '').strip().lower()
            if cleaned in seen_texts:
                issues.append({
                    'issue_type': 'duplicate_question',
                    'severity': 'low',
                    'affected_record': f"Activity: {act.title} (ID: {act.id})",
                    'record_type': 'question',
                    'record_id': q.id,
                    'description': f"Duplicate question text found: \"{q.question_text[:60]}...\"",
                    'suggested_fix': "Edit or remove the redundant question from this activity."
                })
            else:
                seen_texts.add(cleaned)

    # 3. Orphaned questions (activity_id is null or does not match an existing activity)
    questions = ActivityQuestion.query.all()
    for q in questions:
        if q.activity_id is None or q.activity_id not in all_activity_ids:
            issues.append({
                'issue_type': 'orphaned_question',
                'severity': 'high',
                'affected_record': f"Question: \"{q.question_text[:40]}...\" (ID: {q.id})",
                'record_type': 'question',
                'record_id': q.id,
                'description': f"Question ID {q.id} is linked to non-existent activity_id {q.activity_id}.",
                'suggested_fix': "Re-assign this question to an existing activity or delete the orphan record."
            })

    # 4. Translation Completeness & Integrity (Hindi i18n)
    # Detects activities with partial or broken Hindi translation data:
    # - Title translated but some or all questions missing Hindi translations
    # - Questions translated but activity title missing
    # - Option count mismatch between English and Hindi
    # - Correct answer in Hindi missing from Hindi options
    for act in activities:
        act_trans = act.translations or {}
        has_hi_act = 'hi' in act_trans and bool(act_trans['hi'].get('title'))
        act_questions = act.questions.all() if hasattr(act.questions, 'all') else act.questions
        total_q = len(act_questions)

        # Inspect question-level Hindi translations
        q_with_hi = []
        q_missing_hi = []
        for q in act_questions:
            q_trans = q.translations or {}
            if 'hi' in q_trans and bool(q_trans['hi'].get('question_text')):
                q_with_hi.append(q)
            else:
                q_missing_hi.append(q)

        # Check if activity has any Hindi data
        if has_hi_act or q_with_hi:
            # Case A: Activity has Hindi title, but questions lack Hindi translations
            if has_hi_act and q_missing_hi and total_q > 0:
                issues.append({
                    'issue_type': 'incomplete_translation',
                    'severity': 'medium',
                    'affected_record': f"Activity: {act.title} (ID: {act.id})",
                    'record_type': 'activity',
                    'record_id': act.id,
                    'description': (
                        f"Activity #{act.id} ('{act.title}') has Hindi title, but "
                        f"{len(q_missing_hi)} of {total_q} questions lack Hindi translations."
                    ),
                    'suggested_fix': f"Provide complete Hindi translations for all {total_q} questions or remove partial translation."
                })

            # Case B: Questions have Hindi translations, but activity title is missing in Hindi
            if not has_hi_act and q_with_hi:
                issues.append({
                    'issue_type': 'incomplete_translation',
                    'severity': 'medium',
                    'affected_record': f"Activity: {act.title} (ID: {act.id})",
                    'record_type': 'activity',
                    'record_id': act.id,
                    'description': (
                        f"Activity #{act.id} ('{act.title}') has {len(q_with_hi)} translated Hindi questions, "
                        f"but the activity title and description lack Hindi translations."
                    ),
                    'suggested_fix': "Add Hindi translations for the activity title and description."
                })

            # Case C: Question option count mismatch or missing correct answer in Hindi
            for q in q_with_hi:
                q_trans = q.translations.get('hi', {})
                hi_opts = q_trans.get('options') or []
                en_opts = q.options or []

                # Options count mismatch
                if en_opts and len(hi_opts) != len(en_opts):
                    issues.append({
                        'issue_type': 'incomplete_translation',
                        'severity': 'medium',
                        'affected_record': f"Activity: {act.title} (ID: {act.id})",
                        'record_type': 'activity',
                        'record_id': act.id,
                        'description': (
                            f"Activity #{act.id} ('{act.title}') question #{q.order_num} has {len(hi_opts)} "
                            f"Hindi options, but {len(en_opts)} English options (count mismatch)."
                        ),
                        'suggested_fix': f"Provide exactly {len(en_opts)} Hindi options matching the English choices."
                    })

                # Correct answer not in options
                hi_correct = q_trans.get('correct_answer')
                if hi_opts and hi_correct and hi_correct not in hi_opts:
                    issues.append({
                        'issue_type': 'incomplete_translation',
                        'severity': 'medium',
                        'affected_record': f"Activity: {act.title} (ID: {act.id})",
                        'record_type': 'activity',
                        'record_id': act.id,
                        'description': (
                            f"Activity #{act.id} ('{act.title}') question #{q.order_num} Hindi correct answer "
                            f"'{hi_correct}' is not included in its Hindi options list."
                        ),
                        'suggested_fix': f"Update Hindi options to include '{hi_correct}' as a selectable choice."
                    })

    return issues


def get_issue_count() -> int:
    """Convenience helper returning the total count of integrity issues."""
    return len(run_audit())
