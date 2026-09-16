from datetime import datetime, timezone
from app import db
from app.models.child import Child
from app.models.activity import Category, Activity
from app.models.recommendation import Recommendation
from app.services import analytics_service, engagement_service

DIFFICULTY_LEVELS = ['Beginner', 'Easy', 'Medium', 'Advanced']


def get_next_difficulty(current_difficulty):
    """Returns the next higher difficulty level, capping at Advanced."""
    if current_difficulty not in DIFFICULTY_LEVELS:
        return 'Easy'
    idx = DIFFICULTY_LEVELS.index(current_difficulty)
    return DIFFICULTY_LEVELS[min(idx + 1, len(DIFFICULTY_LEVELS) - 1)]


def get_easier_difficulty(current_difficulty):
    """Returns the next easier difficulty level, flooring at Beginner."""
    if current_difficulty not in DIFFICULTY_LEVELS:
        return 'Beginner'
    idx = DIFFICULTY_LEVELS.index(current_difficulty)
    return DIFFICULTY_LEVELS[max(idx - 1, 0)]


def evaluate_rule_based_recommendation(category_accuracy, current_difficulty='Easy', category_name=None):
    """Layer 1: Evaluates category accuracy thresholds to determine difficulty progression."""
    acc = float(category_accuracy)
    acc_int = int(round(acc))
    cat_str = f" in {category_name}" if category_name else ""

    if acc >= 80.0:
        target = get_next_difficulty(current_difficulty)
        rec_type = Recommendation.TYPE_LEVEL_UP
        action_text = f"Ready for the next challenge at {target} level."
        reason = f"Strong recent performance{cat_str} ({acc_int}% accuracy). Ready for the next challenge at {target} level."
    elif acc < 50.0:
        target = get_easier_difficulty(current_difficulty)
        rec_type = Recommendation.TYPE_PRACTICE
        action_text = f"Gentle practice recommended at {target} level to build confidence."
        reason = f"Supported practice recommended{cat_str} ({acc_int}% accuracy) with accessible {target} activities."
    else:
        target = current_difficulty
        rec_type = Recommendation.TYPE_REINFORCE
        action_text = f"Steady progress shown. Reinforce skills with another {target} activity."
        reason = f"Steady progress{cat_str} ({acc_int}% accuracy). Reinforce skills with another {target} activity."

    return {
        'recommendation_type': rec_type,
        'target_difficulty': target,
        'action_text': action_text,
        'reason': reason
    }


def evaluate_performance_based_recommendation(accuracy, completion_rate, current_difficulty='Easy', category_name=None):
    """Layer 2: Adjusts suggested difficulty by assessing accuracy and session completion rate together."""
    acc = float(accuracy)
    comp = float(completion_rate)
    acc_int = int(round(acc))
    comp_int = int(round(comp))
    cat_str = f" in {category_name}" if category_name else ""

    if acc >= 80.0 and comp >= 75.0:
        target = get_next_difficulty(current_difficulty)
        rec_type = Recommendation.TYPE_LEVEL_UP
        reason = f"High accuracy ({acc_int}%) and strong completion ({comp_int}%){cat_str} demonstrate readiness for {target} level."
    elif acc >= 80.0 and comp < 50.0:
        # High accuracy but exited early -> consolidate stamina at current level
        target = current_difficulty
        rec_type = Recommendation.TYPE_REINFORCE
        reason = f"Good accuracy ({acc_int}%), but early exit ({comp_int}% completed){cat_str} suggests practicing at {target} level to build stamina."
    elif acc < 50.0 or comp < 50.0:
        target = get_easier_difficulty(current_difficulty)
        rec_type = Recommendation.TYPE_PRACTICE
        reason = f"Supported practice recommended{cat_str} ({acc_int}% accuracy, {comp_int}% completion) with accessible {target} activities."
    else:
        target = current_difficulty
        rec_type = Recommendation.TYPE_REINFORCE
        reason = f"Balanced engagement{cat_str} ({acc_int}% accuracy, {comp_int}% completion). Keep reinforcing skills at {target} level."

    return {
        'recommendation_type': rec_type,
        'target_difficulty': target,
        'reason': reason
    }


def get_recommendations_for_child(child_id, persist=True):
    """Layer 3: Synthesizes performance history, engagement, and category breadth into top 3-5 ranked recommendations."""
    child = db.session.get(Child, child_id)
    child_age = child.age if child else None

    df = analytics_service.load_child_session_dataframe(child_id)
    all_categories = Category.query.order_by(Category.id).all()
    recommendations_list = []

    # Cold start: if child has no sessions, recommend introductory activities matching age band
    if df.empty:
        for idx, cat in enumerate(all_categories[:3]):
            q = Activity.query.filter(Activity.category_id == cat.id, Activity.is_active.is_(True))
            if child_age is not None:
                q = q.filter(Activity.min_age <= child_age, Activity.max_age >= child_age)
            act = q.filter(Activity.difficulty.in_(['Beginner', 'Easy'])).order_by(Activity.min_age, Activity.difficulty).first()
            if not act:
                act = q.first()
            if act:
                recommendations_list.append({
                    'child_id': child_id,
                    'activity_id': act.id,
                    'activity_title': act.title,
                    'category_name': cat.name,
                    'category_slug': cat.slug,
                    'difficulty': act.difficulty,
                    'recommendation_type': Recommendation.TYPE_EXPLORE,
                    'reason': f"Welcome to {cat.name}! 0 sessions completed so far. Start your learning journey with an introductory {act.difficulty} activity.",
                    'priority': idx + 1
                })
    else:
        played_activity_ids = set(df['activity_id'].unique())
        candidates = []

        # Evaluate played categories
        for cat in all_categories:
            cat_df = df[df['category_id'] == cat.id]
            if not cat_df.empty:
                cat_acc = analytics_service.compute_overall_accuracy(cat_df)
                cat_comp = analytics_service.compute_completion_rate(cat_df)
                cat_eng = engagement_service.compute_category_engagement(child_id, cat.id)

                # Determine current highest difficulty played in this category from chronological sessions
                last_act_id = int(cat_df.sort_values(by='session_id', ascending=False).iloc[0]['activity_id'])
                last_activity = db.session.get(Activity, last_act_id)
                curr_diff = last_activity.difficulty if last_activity else 'Easy'

                perf_eval = evaluate_performance_based_recommendation(cat_acc, cat_comp, curr_diff, category_name=cat.name)
                target_diff = perf_eval['target_difficulty']

                # Base query scoped to category, active status, and child age band
                base_q = Activity.query.filter(
                    Activity.category_id == cat.id,
                    Activity.is_active.is_(True)
                )
                if child_age is not None:
                    base_q = base_q.filter(Activity.min_age <= child_age, Activity.max_age >= child_age)

                # Find candidate activity matching target difficulty and unplayed
                candidate_act = base_q.filter(
                    Activity.difficulty == target_diff,
                    ~Activity.id.in_(played_activity_ids)
                ).first()

                # Fallback to any unplayed in category/age band, then target diff in age band, then any in age band
                if not candidate_act:
                    candidate_act = base_q.filter(~Activity.id.in_(played_activity_ids)).first()
                if not candidate_act:
                    candidate_act = base_q.filter(Activity.difficulty == target_diff).first()
                if not candidate_act:
                    candidate_act = base_q.first()

                if candidate_act:
                    # Score priority based on performance and engagement
                    candidates.append({
                        'activity': candidate_act,
                        'category': cat,
                        'reason': f"{perf_eval['reason']} Let's try {candidate_act.title} in {cat.name}.",
                        'recommendation_type': perf_eval['recommendation_type'],
                        'weight': (cat_acc * 0.5) + (cat_eng * 0.5),
                        'is_new': False
                    })
            else:
                # Unexplored category candidate appropriate for child age
                uq = Activity.query.filter(
                    Activity.category_id == cat.id,
                    Activity.is_active.is_(True)
                )
                if child_age is not None:
                    uq = uq.filter(Activity.min_age <= child_age, Activity.max_age >= child_age)

                unexplored_act = uq.filter(Activity.difficulty.in_(['Beginner', 'Easy'])).first() or uq.first()

                if unexplored_act:
                    candidates.append({
                        'activity': unexplored_act,
                        'category': cat,
                        'reason': f"Expand your curiosity! Explore {cat.name} (0 sessions completed so far) with an engaging introductory {unexplored_act.difficulty} activity.",
                        'recommendation_type': Recommendation.TYPE_EXPLORE,
                        'weight': 65.0,  # Prioritize balanced exploration
                        'is_new': True
                    })

        # Rank candidates: balance top performance, practice needs, and novelty
        candidates.sort(key=lambda c: c['weight'], reverse=True)

        # Pick top 3 to 5 unique activities
        seen_act_ids = set()
        priority_counter = 1
        for item in candidates:
            act = item['activity']
            if act.id not in seen_act_ids:
                seen_act_ids.add(act.id)
                from app.agent import compliance_agent
                clean_reason = compliance_agent.enforce_compliance(
                    item['reason'],
                    context={
                        'source': 'recommendation',
                        'child_id': child_id,
                        'activity_id': act.id
                    },
                    fallback_text=f"Practice recommended to reinforce {item['category'].name} skills at {act.difficulty} level."
                )
                recommendations_list.append({
                    'child_id': child_id,
                    'activity_id': act.id,
                    'activity_title': act.title,
                    'category_name': item['category'].name,
                    'category_slug': item['category'].slug,
                    'difficulty': act.difficulty,
                    'recommendation_type': item['recommendation_type'],
                    'reason': clean_reason,
                    'priority': priority_counter
                })
                priority_counter += 1
                if len(recommendations_list) >= 5:
                    break

    # Persist to database if requested
    if persist:
        # Clear existing automated recommendations for this child, preserving teacher assignments
        existing_recs = Recommendation.query.filter_by(child_id=child_id).all()
        for r in existing_recs:
            if 'Assigned by teacher' not in r.reason:
                db.session.delete(r)
        db.session.commit()

        now = datetime.now(timezone.utc)
        from app.agent import compliance_agent
        for rec_data in recommendations_list:
            clean_reason = compliance_agent.enforce_compliance(
                rec_data['reason'],
                context={
                    'source': 'recommendation',
                    'child_id': child_id,
                    'activity_id': rec_data['activity_id']
                },
                fallback_text=f"Practice recommended to reinforce skills at {rec_data['difficulty']} level."
            )
            rec = Recommendation(
                child_id=child_id,
                activity_id=rec_data['activity_id'],
                reason=clean_reason,
                recommendation_type=rec_data['recommendation_type'],
                priority=rec_data['priority'],
                created_at=now
            )
            db.session.add(rec)
        db.session.commit()

        # Trigger in-dashboard notification for parent
        try:
            from app.services import notification_service
            notification_service.notify_recommendation_generated(child_id, recommendations_list)
        except Exception:
            pass

    return recommendations_list


# Alias for backwards compatibility
generate_personalized_recommendations = get_recommendations_for_child
