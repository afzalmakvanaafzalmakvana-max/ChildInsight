"""
Adaptive Content Suggestion Agent (app/agent/content_suggestion_agent.py)

Analyzes platform-wide aggregate child demographics (Child.age distributions)
and category performance metrics to detect educational content gaps:
1. Progression gaps: Children clustering at one difficulty tier where the next tier lacks content.
2. Age coverage gaps: Categories lacking activities for age groups active on the platform.
3. Content imbalances: Categories with significantly lower activity counts than the platform average.
4. Domain expansion: High-utilization opportunities for new learning categories.

IMPORTANT: This agent NEVER auto-creates or auto-publishes content. It generates
structured recommendations stored in `content_suggestions` for human review.
"""

from datetime import datetime, timezone
import logging
from app import db
from app.models.child import Child
from app.models.activity import Category, Activity
from app.models.session import ActivitySession
from app.models.content_suggestion import ContentSuggestion
from app.translations import normalize_language
from app.services import analytics_service

logger = logging.getLogger('childinsight.content_suggestion_agent')


def calculate_priority_score(affected_count: int, persistence_count: int, trend: str = 'steady') -> float:
    """
    Calculates priority urgency score based on affected children, persistence across scheduler runs,
    and engagement trend.
    Formula: (affected_count * 2.0) + (persistence_count * 5.0) + (5.0 if trend == 'declining' else 0.0)
    """
    score = (float(affected_count) * 2.0) + (float(persistence_count) * 5.0)
    if trend == 'declining':
        score += 5.0
    return round(float(score), 1)

AGE_BANDS = [
    (4, 6, '4-6', 'Early Childhood / Pre-K'),
    (6, 9, '6-9', 'Early Elementary'),
    (9, 12, '9-12', 'Upper Elementary'),
    (12, 14, '12-14', 'Early Secondary')
]

DIFFICULTY_PROGRESSION = {
    'Beginner': 'Easy',
    'Easy': 'Medium',
    'Medium': 'Advanced'
}


def get_age_band_for_age(age: int) -> tuple | None:
    """Map a child age to standard age band tuple (min, max, label, desc)."""
    if age is None:
        return None
    for min_a, max_a, label, desc in AGE_BANDS:
        if min_a <= age <= max_a:
            return (min_a, max_a, label, desc)
    return None


def analyze_platform_data() -> dict:
    """
    Collects aggregate learner demographics and content distribution metrics,
    including language preferences and translation coverage.
    Returns structured analysis payload used by suggestion heuristics.
    """
    # 1. Demographics: Count learners in each age band (overall and Hindi-preferring)
    all_children = Child.query.all()
    age_counts = {'4-6': 0, '6-9': 0, '9-12': 0, '12-14': 0, 'other': 0}
    children_by_band = {'4-6': [], '6-9': [], '9-12': [], '12-14': []}
    hindi_age_counts = {'4-6': 0, '6-9': 0, '9-12': 0, '12-14': 0, 'other': 0}
    hindi_children_by_band = {'4-6': [], '6-9': [], '9-12': [], '12-14': []}

    for child in all_children:
        is_hindi = normalize_language(child.preferred_language) == 'hi'
        band_info = get_age_band_for_age(child.age)
        if band_info:
            band_label = band_info[2]
            age_counts[band_label] += 1
            children_by_band[band_label].append(child)
            if is_hindi:
                hindi_age_counts[band_label] += 1
                hindi_children_by_band[band_label].append(child)
        else:
            age_counts['other'] += 1
            if is_hindi:
                hindi_age_counts['other'] += 1

    # 2. Activity catalog distribution per category and age band (including Hindi translations)
    categories = Category.query.all()
    cat_metrics = {}
    total_activities = Activity.query.filter_by(is_active=True).count()
    avg_activities_per_cat = (total_activities / len(categories)) if categories else 0

    for cat in categories:
        active_acts = Activity.query.filter_by(category_id=cat.id, is_active=True).all()
        by_age = {'4-6': 0, '6-9': 0, '9-12': 0, '12-14': 0}
        by_diff = {'Beginner': 0, 'Easy': 0, 'Medium': 0, 'Advanced': 0}
        by_band_and_diff = {}
        by_age_translated = {'4-6': 0, '6-9': 0, '9-12': 0, '12-14': 0}

        for act in active_acts:
            by_diff[act.difficulty] = by_diff.get(act.difficulty, 0) + 1
            has_hi = act.has_translation('hi')
            for min_a, max_a, label, _ in AGE_BANDS:
                if act.min_age <= max_a and act.max_age >= min_a:
                    by_age[label] += 1
                    key = (label, act.difficulty)
                    by_band_and_diff[key] = by_band_and_diff.get(key, 0) + 1
                    if has_hi:
                        by_age_translated[label] += 1

        cat_metrics[cat.id] = {
            'category': cat,
            'total_count': len(active_acts),
            'by_age': by_age,
            'by_diff': by_diff,
            'by_band_and_diff': by_band_and_diff,
            'by_age_translated': by_age_translated
        }

    return {
        'total_learners': len(all_children),
        'age_counts': age_counts,
        'children_by_band': children_by_band,
        'hindi_age_counts': hindi_age_counts,
        'hindi_children_by_band': hindi_children_by_band,
        'categories': categories,
        'cat_metrics': cat_metrics,
        'avg_activities_per_cat': avg_activities_per_cat
    }


def detect_gaps(analysis: dict) -> list:
    """
    Applies educational content gap heuristics across analyzed platform data:
    1. Progression Bottlenecks
    2. Age Coverage Gaps
    3. Category Content Imbalances
    4. Domain Expansion Opportunities

    Calculates exact affected children counts, gap persistence across runs,
    and engagement trends from analytics_service.
    """
    suggestions = []
    cat_metrics = analysis['cat_metrics']
    age_counts = analysis['age_counts']
    children_by_band = analysis['children_by_band']
    avg_acts = analysis['avg_activities_per_cat']

    # -------------------------------------------------------------------------
    # Heuristic 1: Progression Bottlenecks
    # Detects when children in an age band perform well at difficulty D in category C,
    # but the next difficulty tier has <= 1 active activities available.
    # -------------------------------------------------------------------------
    for cat_id, c_data in cat_metrics.items():
        category = c_data['category']
        for min_a, max_a, band_label, _ in AGE_BANDS:
            band_kids = children_by_band.get(band_label, [])
            if not band_kids:
                continue

            for curr_diff, next_diff in DIFFICULTY_PROGRESSION.items():
                next_count = c_data['by_band_and_diff'].get((band_label, next_diff), 0)

                # Check performance of children in this category at current difficulty
                kid_ids = [k.id for k in band_kids]

                # Check completed sessions in this category for these children
                sessions = ActivitySession.query.join(Activity, ActivitySession.activity_id == Activity.id).filter(
                    ActivitySession.child_id.in_(kid_ids),
                    Activity.category_id == cat_id,
                    Activity.difficulty == curr_diff,
                    ActivitySession.status == ActivitySession.STATUS_COMPLETED
                ).all()

                if sessions:
                    avg_acc = sum(s.accuracy for s in sessions) / len(sessions)
                    # If high accuracy (>=70%) or 3+ sessions completed, and next tier is sparse (<= 1 activity)
                    if (avg_acc >= 70.0 or len(sessions) >= 3) and next_count <= 1:
                        affected_kids = len(set(s.child_id for s in sessions)) or len(band_kids)
                        trend = analytics_service.compute_category_age_band_engagement_trend(cat_id, band_label)

                        def make_progression_reason(runs, aff=affected_kids, acc=avg_acc, n_cnt=next_count, tr=trend, c_name=category.name, c_diff=curr_diff, n_diff=next_diff, b_lbl=band_label):
                            trend_desc = f"with a {tr} engagement trend" if tr != 'steady' else "with steady engagement"
                            return (
                                f"{aff} children aged {b_lbl} are averaging {acc:.0f}% accuracy in {c_diff} {c_name} "
                                f"{trend_desc}, but only {n_cnt} {n_diff} activity(ies) available — "
                                f"this gap has persisted for {runs} scheduler run(s)."
                            )

                        priority = calculate_priority_score(affected_kids, 1, trend)
                        suggestions.append({
                            'suggestion_type': ContentSuggestion.TYPE_PROGRESSION_GAP,
                            'category_id': category.id,
                            'age_band': band_label,
                            'target_difficulty': next_diff,
                            'suggested_title': f"{category.name} {next_diff} Challenge",
                            'affected_children_count': affected_kids,
                            'trend': trend,
                            'priority_score': priority,
                            'format_reason': make_progression_reason,
                            'reason': make_progression_reason(1)
                        })

    # -------------------------------------------------------------------------
    # Heuristic 2: Age Coverage Gaps
    # Detects when an age group is represented on the platform, but a category
    # has fewer than 2 activities supporting that age group.
    # -------------------------------------------------------------------------
    for cat_id, c_data in cat_metrics.items():
        category = c_data['category']
        for min_a, max_a, band_label, desc in AGE_BANDS:
            learner_count = age_counts.get(band_label, 0)
            act_count = c_data['by_age'].get(band_label, 0)

            # If learners exist for this age band, but category has < 2 activities
            if learner_count > 0 and act_count < 2:
                # Default suggested difficulty based on age band
                default_diff = 'Beginner' if band_label == '4-6' else ('Easy' if band_label == '6-9' else ('Medium' if band_label == '9-12' else 'Advanced'))
                trend = analytics_service.compute_category_age_band_engagement_trend(cat_id, band_label)

                def make_age_reason(runs, aff=learner_count, a_cnt=act_count, tr=trend, c_name=category.name, b_lbl=band_label, b_desc=desc):
                    trend_clause = f" (engagement trend: {tr})" if tr != 'steady' else ""
                    return (
                        f"{aff} registered learner(s) in age band {b_lbl} ({b_desc}) currently have only "
                        f"{a_cnt} activity(ies) available in '{c_name}'{trend_clause} — "
                        f"this gap has persisted for {runs} scheduler run(s). "
                        f"Expanding content for age band {b_lbl} will ensure age-appropriate learning coverage."
                    )

                priority = calculate_priority_score(learner_count, 1, trend)
                suggestions.append({
                    'suggestion_type': ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
                    'category_id': category.id,
                    'age_band': band_label,
                    'target_difficulty': default_diff,
                    'suggested_title': f"{category.name} for Ages {band_label}",
                    'affected_children_count': learner_count,
                    'trend': trend,
                    'priority_score': priority,
                    'format_reason': make_age_reason,
                    'reason': make_age_reason(1)
                })

    # -------------------------------------------------------------------------
    # Heuristic 3: Category Content Imbalance
    # Detects categories with an activity count significantly below platform average.
    # -------------------------------------------------------------------------
    for cat_id, c_data in cat_metrics.items():
        category = c_data['category']
        count = c_data['total_count']

        # If a category has fewer than 5 activities, or is more than 40% below platform average
        if count < 5 or (avg_acts > 5 and count < avg_acts * 0.6):
            # Check which age bands are affected in this category
            affected = [label for _, _, label, _ in AGE_BANDS if c_data['by_age'].get(label, 0) < 2]
            if not affected or len(affected) == 4:
                band_tag = 'All (4-14)'
                affected_kids = analysis['total_learners']
            else:
                band_tag = ', '.join(affected)
                affected_kids = sum(age_counts.get(b, 0) for b in affected) or analysis['total_learners']

            trend = analytics_service.compute_category_age_band_engagement_trend(cat_id, band_tag)

            def make_imbalance_reason(runs, aff=affected_kids, cnt=count, avg=avg_acts, tr=trend, c_name=category.name, b_tag=band_tag):
                trend_clause = f" (engagement trend: {tr})" if tr != 'steady' else ""
                return (
                    f"{aff} learner(s) affected across age band(s) {b_tag}: category '{c_name}' currently has only "
                    f"{cnt} total activity(ies) (substantially below platform average of {avg:.1f}{trend_clause}) — "
                    f"this gap has persisted for {runs} scheduler run(s). Adding introductory activities will balance the educational catalog."
                )

            priority = calculate_priority_score(affected_kids, 1, trend)
            suggestions.append({
                'suggestion_type': ContentSuggestion.TYPE_CONTENT_IMBALANCE,
                'category_id': category.id,
                'age_band': band_tag,
                'target_difficulty': 'Easy',
                'suggested_title': f"{category.name} Exploration",
                'affected_children_count': affected_kids,
                'trend': trend,
                'priority_score': priority,
                'format_reason': make_imbalance_reason,
                'reason': make_imbalance_reason(1)
            })

    # -------------------------------------------------------------------------
    # Heuristic 4: Domain Expansion Opportunity
    # If the platform has strong content and learners across all existing domains,
    # suggest expanding into adjacent domains (e.g. Science & Nature).
    # -------------------------------------------------------------------------
    existing_slugs = {c.slug for c in analysis['categories']}
    if 'science' not in existing_slugs and len(analysis['categories']) >= 5:
        # Check if platform has active sessions
        total_sessions = ActivitySession.query.count()
        if total_sessions >= 10:
            total_learners = analysis['total_learners']
            trend = analytics_service.compute_category_age_band_engagement_trend(None, None)

            def make_new_cat_reason(runs, aff=total_learners, sess=total_sessions, c_cnt=len(analysis['categories']), tr=trend):
                trend_clause = f" (platform engagement trend: {tr})" if tr != 'steady' else ""
                return (
                    f"{aff} active learner(s) across all {c_cnt} cognitive categories with {sess} completed learning sessions recorded{trend_clause} — "
                    f"introducing 'Science & Nature' for all age bands (4-14) has been recommended across {runs} scheduler run(s) "
                    f"to enrich STEM inquiry without overloading existing cognitive domains."
                )

            priority = calculate_priority_score(total_learners, 1, trend)
            suggestions.append({
                'suggestion_type': ContentSuggestion.TYPE_NEW_CATEGORY,
                'category_id': None,
                'age_band': 'All (4-14)',
                'target_difficulty': None,
                'suggested_title': 'Science & Nature',
                'affected_children_count': total_learners,
                'trend': trend,
                'priority_score': priority,
                'format_reason': make_new_cat_reason,
                'reason': make_new_cat_reason(1)
            })

    # -------------------------------------------------------------------------
    # Heuristic 5: Translation Gaps
    # Detects when Hindi-preferring learners are registered in an age band, but
    # a category has little or no translated content available (< 2 translated activities).
    # Uses exact computed database metrics: real child counts, real translated activity
    # counts, real total activities, and exact calculated translation percentages.
    # -------------------------------------------------------------------------
    hindi_age_counts = analysis.get('hindi_age_counts', {})
    for cat_id, c_data in cat_metrics.items():
        category = c_data['category']
        for min_a, max_a, band_label, desc in AGE_BANDS:
            hindi_count = hindi_age_counts.get(band_label, 0)
            if hindi_count == 0:
                continue

            act_count = c_data['by_age'].get(band_label, 0)
            translated_count = c_data.get('by_age_translated', {}).get(band_label, 0)

            # Translation gap condition:
            # Active Hindi learners in this band, but < 2 translated activities in this category
            if translated_count < 2:
                default_diff = 'Beginner' if band_label == '4-6' else ('Easy' if band_label == '6-9' else ('Medium' if band_label == '9-12' else 'Advanced'))
                trend = analytics_service.compute_category_age_band_engagement_trend(cat_id, band_label)
                trans_pct = (translated_count / act_count * 100.0) if act_count > 0 else 0.0

                def make_trans_reason(runs, aff=hindi_count, t_cnt=translated_count, a_cnt=act_count, pct=trans_pct, tr=trend, c_name=category.name, b_lbl=band_label, b_desc=desc):
                    trend_clause = f" (cohort engagement trend: {tr})" if tr != 'steady' else ""
                    return (
                        f"{aff} registered learner(s) in age band {b_lbl} ({b_desc}) prefer Hindi, but category '{c_name}' "
                        f"currently has only {t_cnt} translated Hindi activity(ies) out of {a_cnt} total activities ({pct:.0f}% translated){trend_clause} — "
                        f"this translation gap has persisted for {runs} scheduler run(s). "
                        f"Translating or authoring Hindi content for age band {b_lbl} will ensure native-language cognitive access."
                    )

                priority = calculate_priority_score(hindi_count, 1, trend)
                suggestions.append({
                    'suggestion_type': ContentSuggestion.TYPE_TRANSLATION_GAP,
                    'category_id': category.id,
                    'age_band': band_label,
                    'target_difficulty': default_diff,
                    'suggested_title': f"{category.name} in Hindi for Ages {band_label}",
                    'affected_children_count': hindi_count,
                    'trend': trend,
                    'priority_score': priority,
                    'format_reason': make_trans_reason,
                    'reason': make_trans_reason(1)
                })

    return suggestions


def get_covered_age_bands(band_str: str | None) -> set[str]:
    """
    Returns the set of standard age band labels ('4-6', '6-9', '9-12', '12-14')
    covered by the given band_str.
    """
    all_labels = {'4-6', '6-9', '9-12', '12-14'}
    if not band_str:
        return all_labels
    norm = band_str.lower()
    if 'all' in norm:
        return all_labels
    covered = set()
    for label in all_labels:
        if label in band_str:
            covered.add(label)
    if not covered:
        import re
        nums = [int(n) for n in re.findall(r'\d+', band_str)]
        if len(nums) >= 2:
            min_v, max_v = min(nums), max(nums)
            for min_a, max_a, label, _ in AGE_BANDS:
                if max(min_a, min_v) <= min(max_a, max_v):
                    covered.add(label)
        elif len(nums) == 1:
            v = nums[0]
            for min_a, max_a, label, _ in AGE_BANDS:
                if min_a <= v <= max_a:
                    covered.add(label)
    return covered if covered else all_labels


def age_bands_overlap(band_a: str | None, band_b: str | None) -> bool:
    """Returns True if two age band strings cover at least one common age band."""
    bands_a = get_covered_age_bands(band_a)
    bands_b = get_covered_age_bands(band_b)
    return bool(bands_a.intersection(bands_b))


def gap_affects_age_band(gap_age_band: str | None, target_band: str) -> bool:
    """Returns True if the gap's age_band tag affects the specified target age band."""
    if not gap_age_band:
        return True  # Legacy untagged suggestions affect all bands
    norm = gap_age_band.lower()
    if 'all' in norm:
        return True
    return target_band in gap_age_band


def consolidate_gap_specs(gap_specs: list, categories: list = None) -> list:
    """
    Consolidates gap specs so that if multiple heuristics detect a gap for the
    same category and overlapping age bands, only ONE consolidated suggestion is produced.
    Merges reasons, updates affected counts, and selects primary representative metadata.
    """
    if not gap_specs:
        return []

    if categories is None:
        categories = Category.query.all()
    cat_by_name = {c.name.strip().lower(): c for c in categories}
    cat_by_slug = {c.slug.strip().lower(): c for c in categories}

    # Normalize category_id if missing but suggested_title matches an existing category
    for spec in gap_specs:
        if spec.get('category_id') is None and spec.get('suggested_title'):
            t_norm = spec['suggested_title'].strip().lower()
            matched = cat_by_name.get(t_norm) or cat_by_slug.get(t_norm)
            if not matched:
                for c in categories:
                    if c.name.lower() in t_norm or t_norm in c.name.lower():
                        matched = c
                        break
            if matched:
                spec['category_id'] = matched.id

    # Group specs by category key and gap modality (translation vs standard)
    grouped_by_cat = {}
    for spec in gap_specs:
        cid = spec.get('category_id')
        is_trans = (spec.get('suggestion_type') == ContentSuggestion.TYPE_TRANSLATION_GAP)
        trans_suffix = "_trans" if is_trans else ""
        if cid is not None:
            key = f"cat_{cid}{trans_suffix}"
        else:
            title = (spec.get('suggested_title') or '').strip().lower()
            key = f"new_{title}{trans_suffix}"
        grouped_by_cat.setdefault(key, []).append(spec)

    consolidated_specs = []

    for cat_key, cat_specs in grouped_by_cat.items():
        # Partition cat_specs into connected clusters based on overlapping age bands
        clusters = []
        for spec in cat_specs:
            spec_band = spec.get('age_band')
            matching_cluster_indices = []
            for idx, cluster in enumerate(clusters):
                if any(age_bands_overlap(s.get('age_band'), spec_band) for s in cluster):
                    matching_cluster_indices.append(idx)

            if not matching_cluster_indices:
                clusters.append([spec])
            else:
                first_idx = matching_cluster_indices[0]
                clusters[first_idx].append(spec)
                for other_idx in sorted(matching_cluster_indices[1:], reverse=True):
                    clusters[first_idx].extend(clusters.pop(other_idx))

        # Consolidate each cluster into one spec
        for cluster in clusters:
            if len(cluster) == 1:
                consolidated_specs.append(cluster[0])
                continue

            # Multiple specs detected for this category with overlapping age bands
            all_covered = set()
            for s in cluster:
                all_covered.update(get_covered_age_bands(s.get('age_band')))

            standard_order = ['4-6', '6-9', '9-12', '12-14']
            sorted_covered = [b for b in standard_order if b in all_covered]

            prog_specs = [s for s in cluster if s.get('suggestion_type') == ContentSuggestion.TYPE_PROGRESSION_GAP]
            age_specs = [s for s in cluster if s.get('suggestion_type') == ContentSuggestion.TYPE_AGE_COVERAGE_GAP and 'all' not in (s.get('age_band') or '').lower()]

            if prog_specs:
                primary_spec = max(prog_specs, key=lambda s: s.get('priority_score', 0))
                merged_age_band = primary_spec.get('age_band')
            elif len(age_specs) == 1 and not (len(cluster) >= 3 and len(all_covered) >= 3):
                primary_spec = age_specs[0]
                merged_age_band = primary_spec.get('age_band')
            else:
                type_priority = {
                    ContentSuggestion.TYPE_CONTENT_IMBALANCE: 4,
                    ContentSuggestion.TYPE_NEW_CATEGORY: 3,
                    ContentSuggestion.TYPE_AGE_COVERAGE_GAP: 2,
                    ContentSuggestion.TYPE_PROGRESSION_GAP: 1
                }
                primary_spec = max(
                    cluster,
                    key=lambda s: (type_priority.get(s.get('suggestion_type'), 0), s.get('priority_score', 0))
                )
                if len(sorted_covered) == 4 or any('all' in (s.get('age_band') or '').lower() for s in cluster):
                    merged_age_band = 'All (4-14)'
                elif len(sorted_covered) == 1:
                    merged_age_band = sorted_covered[0]
                else:
                    merged_age_band = ', '.join(sorted_covered)

            max_affected = max(s.get('affected_children_count', 0) for s in cluster)
            if any(s.get('trend') == 'declining' for s in cluster):
                merged_trend = 'declining'
            elif any(s.get('trend') == 'improving' for s in cluster):
                merged_trend = 'improving'
            else:
                merged_trend = 'steady'

            other_types = {s.get('suggestion_type') for s in cluster if s.get('suggestion_type') != primary_spec.get('suggestion_type')}

            def make_merged_reason(runs, p_spec=primary_spec, o_types=other_types, c_specs=cluster):
                if callable(p_spec.get('format_reason')):
                    base_reason = p_spec['format_reason'](runs)
                else:
                    base_reason = p_spec.get('reason', '')

                if o_types:
                    type_names = [t.replace('_', ' ') for t in sorted(o_types)]
                    addon = f" (Consolidated across overlapping age bands with related {', '.join(type_names)} observations)."
                    return f"{base_reason.rstrip('.')} —{addon}"
                return base_reason

            merged_priority = calculate_priority_score(max_affected, 1, merged_trend)

            merged_spec = {
                'suggestion_type': primary_spec['suggestion_type'],
                'category_id': primary_spec.get('category_id'),
                'age_band': merged_age_band,
                'target_difficulty': primary_spec.get('target_difficulty') or 'Easy',
                'suggested_title': primary_spec.get('suggested_title'),
                'affected_children_count': max_affected,
                'trend': merged_trend,
                'priority_score': merged_priority,
                'format_reason': make_merged_reason,
                'reason': make_merged_reason(1)
            }
            consolidated_specs.append(merged_spec)

    return consolidated_specs


def cleanup_duplicate_pending_suggestions() -> int:
    """
    Cleans up any duplicate pending suggestions currently in the database for the same
    category and overlapping age bands. Merges their persistence counts and leaves at most
    one consolidated pending suggestion per category + age_band combination.
    Returns the count of duplicate rows deleted.
    """
    pending = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_PENDING).all()
    if not pending:
        return 0

    categories = Category.query.all()
    cat_by_name = {c.name.strip().lower(): c for c in categories}
    cat_by_slug = {c.slug.strip().lower(): c for c in categories}

    for s in pending:
        if s.category_id is None and s.suggested_title:
            t_norm = s.suggested_title.strip().lower()
            matched = cat_by_name.get(t_norm) or cat_by_slug.get(t_norm)
            if not matched:
                for c in categories:
                    if c.name.lower() in t_norm or t_norm in c.name.lower():
                        matched = c
                        break
            if matched:
                s.category_id = matched.id

    grouped = {}
    for s in pending:
        key = f"cat_{s.category_id}" if s.category_id is not None else f"title_{(s.suggested_title or '').strip().lower()}"
        grouped.setdefault(key, []).append(s)

    deleted_count = 0

    for key, s_list in grouped.items():
        if len(s_list) <= 1:
            continue

        clusters = []
        for s in s_list:
            matching_cluster_indices = []
            for idx, cluster in enumerate(clusters):
                if any(age_bands_overlap(existing.age_band, s.age_band) for existing in cluster):
                    matching_cluster_indices.append(idx)

            if not matching_cluster_indices:
                clusters.append([s])
            else:
                first_idx = matching_cluster_indices[0]
                clusters[first_idx].append(s)
                for other_idx in sorted(matching_cluster_indices[1:], reverse=True):
                    clusters[first_idx].extend(clusters.pop(other_idx))

        for cluster in clusters:
            if len(cluster) <= 1:
                continue

            prog_specs = [s for s in cluster if s.suggestion_type == ContentSuggestion.TYPE_PROGRESSION_GAP]
            age_specs = [s for s in cluster if s.suggestion_type == ContentSuggestion.TYPE_AGE_COVERAGE_GAP and 'all' not in (s.age_band or '').lower()]

            all_covered = set()
            for s in cluster:
                all_covered.update(get_covered_age_bands(s.age_band))
            standard_order = ['4-6', '6-9', '9-12', '12-14']
            sorted_covered = [b for b in standard_order if b in all_covered]

            if prog_specs:
                primary = max(prog_specs, key=lambda s: (s.priority_score or 0.0, s.persistence_count or 1))
            elif len(age_specs) == 1 and not (len(cluster) >= 3 and len(all_covered) >= 3):
                primary = age_specs[0]
            else:
                type_priority = {
                    ContentSuggestion.TYPE_CONTENT_IMBALANCE: 4,
                    ContentSuggestion.TYPE_NEW_CATEGORY: 3,
                    ContentSuggestion.TYPE_AGE_COVERAGE_GAP: 2,
                    ContentSuggestion.TYPE_PROGRESSION_GAP: 1
                }
                primary = max(cluster, key=lambda s: (type_priority.get(s.suggestion_type, 0), s.priority_score or 0.0, s.persistence_count or 1))
                if len(sorted_covered) == 4 or any('all' in (s.age_band or '').lower() for s in cluster):
                    primary.age_band = 'All (4-14)'
                elif len(sorted_covered) == 1:
                    primary.age_band = sorted_covered[0]
                else:
                    primary.age_band = ', '.join(sorted_covered)

            primary.persistence_count = max(s.persistence_count or 1 for s in cluster)
            primary.priority_score = max(s.priority_score or 0.0 for s in cluster)

            for s in cluster:
                if s.id != primary.id:
                    db.session.delete(s)
                    deleted_count += 1

    if deleted_count > 0:
        db.session.commit()
    return deleted_count


def generate_suggestions(persist: bool = True) -> list:
    """
    Executes platform analysis and persists new or updated non-duplicate suggestions.
    Consolidates overlapping age band suggestions for the same category across heuristics
    so that at most one pending suggestion per category + age_band combination is produced.
    Calculates affected child counts, gap persistence across runs, and priority scores.
    Returns list of active pending ContentSuggestion records sorted by priority_score descending.
    """
    if persist:
        cleanup_duplicate_pending_suggestions()

    analysis = analyze_platform_data()
    raw_specs = detect_gaps(analysis)
    gap_specs = consolidate_gap_specs(raw_specs, analysis.get('categories'))
    persisted_suggestions = []

    for spec in gap_specs:
        pending_query = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_PENDING)
        spec_cat_id = spec.get('category_id')
        spec_title = spec.get('suggested_title')

        if spec_cat_id is not None:
            cat_pending = pending_query.filter(
                (ContentSuggestion.category_id == spec_cat_id) |
                ((ContentSuggestion.category_id == None) & (ContentSuggestion.suggested_title == spec_title))
            ).all()
        else:
            cat_pending = pending_query.filter_by(suggested_title=spec_title).all()

        matching_existing = [
            e for e in cat_pending
            if age_bands_overlap(e.age_band, spec.get('age_band'))
        ]

        if matching_existing:
            existing = max(
                matching_existing,
                key=lambda e: (1 if e.suggestion_type == spec['suggestion_type'] else 0, e.persistence_count or 1)
            )
            existing.persistence_count = (existing.persistence_count or 1) + 1
            existing.priority_score = calculate_priority_score(
                spec.get('affected_children_count', 0),
                existing.persistence_count,
                spec.get('trend', 'steady')
            )
            if spec.get('age_band') == 'All (4-14)':
                existing.age_band = 'All (4-14)'
                if spec['suggestion_type'] == ContentSuggestion.TYPE_CONTENT_IMBALANCE:
                    existing.suggestion_type = ContentSuggestion.TYPE_CONTENT_IMBALANCE
                    existing.suggested_title = spec.get('suggested_title')
            elif not existing.age_band:
                existing.age_band = spec.get('age_band')

            if callable(spec.get('format_reason')):
                existing.reason = spec['format_reason'](existing.persistence_count)
            elif spec.get('reason'):
                existing.reason = spec['reason']

            if persist:
                for duplicate in matching_existing:
                    if duplicate.id != existing.id:
                        db.session.delete(duplicate)

            if existing not in persisted_suggestions:
                persisted_suggestions.append(existing)
            continue

        new_persistence = 1
        priority = calculate_priority_score(
            spec.get('affected_children_count', 0),
            new_persistence,
            spec.get('trend', 'steady')
        )
        if callable(spec.get('format_reason')):
            reason_text = spec['format_reason'](new_persistence)
        else:
            reason_text = spec.get('reason', '')

        suggestion = ContentSuggestion(
            suggestion_type=spec['suggestion_type'],
            category_id=spec.get('category_id'),
            age_band=spec.get('age_band'),
            target_difficulty=spec.get('target_difficulty'),
            suggested_title=spec.get('suggested_title'),
            reason=reason_text,
            priority_score=priority,
            persistence_count=new_persistence,
            status=ContentSuggestion.STATUS_PENDING
        )
        if persist:
            db.session.add(suggestion)
        persisted_suggestions.append(suggestion)

    if persist:
        db.session.commit()

    persisted_suggestions.sort(
        key=lambda s: (s.priority_score if s.priority_score is not None else 0.0),
        reverse=True
    )
    return persisted_suggestions


def dismiss_suggestion(suggestion_id: int) -> bool:
    """Marks a suggestion as dismissed."""
    suggestion = db.session.get(ContentSuggestion, suggestion_id)
    if not suggestion:
        return False
    suggestion.status = ContentSuggestion.STATUS_DISMISSED
    db.session.commit()
    return True


def approve_suggestion(suggestion_id: int) -> bool:
    """Marks a suggestion as approved upon fulfillment."""
    suggestion = db.session.get(ContentSuggestion, suggestion_id)
    if not suggestion:
        return False
    suggestion.status = ContentSuggestion.STATUS_APPROVED
    db.session.commit()
    return True
