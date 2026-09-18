import json
from app import db
from app.models.activity import Category, Activity, ActivityQuestion

from app.utils.activity_seeds import SEED_CATEGORIES
from app.utils.activity_translations_seeds import HINDI_ACTIVITY_TRANSLATIONS


def seed_activities():
    """Populates 5 categories with age-appropriate activities across 4 age bands (4-14), flagged as demo data."""
    created_categories = 0
    created_activities = 0
    created_questions = 0

    for cat_data in SEED_CATEGORIES:
        category = Category.query.filter_by(slug=cat_data['slug']).first()
        if not category:
            category = Category(
                name=cat_data['name'],
                slug=cat_data['slug'],
                icon=cat_data['icon'],
                description=cat_data['description']
            )
            db.session.add(category)
            db.session.flush()
            created_categories += 1
        else:
            category.name = cat_data['name']
            category.icon = cat_data['icon']
            category.description = cat_data['description']

        for act_data in cat_data['activities']:
            min_age = act_data.get('min_age', 4)
            max_age = act_data.get('max_age', 14)
            hindi_trans = HINDI_ACTIVITY_TRANSLATIONS.get(act_data['title'])
            trans_payload = None
            if hindi_trans:
                from app.agent import compliance_agent
                t_safe, _ = compliance_agent.check_text(hindi_trans['title'])
                d_safe, _ = compliance_agent.check_text(hindi_trans['description'])
                if t_safe and d_safe:
                    trans_payload = {'hi': {'title': hindi_trans['title'], 'description': hindi_trans['description']}}

            activity = Activity.query.filter_by(category_id=category.id, title=act_data['title']).first()
            if not activity:
                activity = Activity(
                    category_id=category.id,
                    title=act_data['title'],
                    description=act_data['description'],
                    difficulty=act_data['difficulty'],
                    estimated_duration=act_data['duration'],
                    min_age=min_age,
                    max_age=max_age,
                    is_active=True,
                    is_demo=True,
                    translations_json=json.dumps(trans_payload, ensure_ascii=False) if trans_payload else None
                )
                db.session.add(activity)
                db.session.flush()
                created_activities += 1
            else:
                activity.description = act_data['description']
                activity.difficulty = act_data['difficulty']
                activity.estimated_duration = act_data['duration']
                activity.min_age = min_age
                activity.max_age = max_age
                activity.is_active = True
                activity.is_demo = True
                if trans_payload:
                    activity.translations = trans_payload

            for idx, q_data in enumerate(act_data['questions'], start=1):
                q_trans_payload = None
                if hindi_trans and idx <= len(hindi_trans['questions']):
                    qh = hindi_trans['questions'][idx - 1]
                    # Every translated question must pass the Hindi-aware Compliance Agent check before being saved
                    from app.agent import compliance_agent
                    texts_to_check = [qh['text'], qh['answer']] + list(qh['options'])
                    if qh.get('hint'):
                        texts_to_check.append(qh['hint'])

                    if all(compliance_agent.check_text(t)[0] for t in texts_to_check):
                        q_trans_payload = {
                            'hi': {
                                'question_text': qh['text'],
                                'options': qh['options'],
                                'correct_answer': qh['answer'],
                                'hint': qh.get('hint')
                            }
                        }

                question = ActivityQuestion.query.filter_by(
                    activity_id=activity.id,
                    order_num=idx
                ).first()
                if not question:
                    question = ActivityQuestion(
                        activity_id=activity.id,
                        question_text=q_data['text'],
                        question_type='multiple_choice',
                        options_json=json.dumps(q_data['options']),
                        correct_answer=q_data['answer'],
                        hint=q_data.get('hint'),
                        order_num=idx,
                        translations_json=json.dumps(q_trans_payload, ensure_ascii=False) if q_trans_payload else None
                    )
                    db.session.add(question)
                    created_questions += 1
                else:
                    question.question_text = q_data['text']
                    question.options_json = json.dumps(q_data['options'])
                    question.correct_answer = q_data['answer']
                    question.hint = q_data.get('hint')
                    if q_trans_payload:
                        question.translations = q_trans_payload

    # Clean up legacy demo activities not in current SEED_CATEGORIES to ensure age-band integrity
    valid_titles = {act['title'] for cat in SEED_CATEGORIES for act in cat['activities']}
    legacy_demo_acts = Activity.query.filter(Activity.is_demo.is_(True), ~Activity.title.in_(valid_titles)).all()
    if legacy_demo_acts:
        from app.models.session import ActivitySession
        fallback_act = Activity.query.filter(Activity.title.in_(valid_titles)).first()
        for l_act in legacy_demo_acts:
            if fallback_act:
                ActivitySession.query.filter_by(activity_id=l_act.id).update({'activity_id': fallback_act.id})
            ActivityQuestion.query.filter_by(activity_id=l_act.id).delete()
            db.session.delete(l_act)

    db.session.commit()
    return created_categories, created_activities, created_questions


def seed_demo_data(fresh: bool = False):
    """
    Comprehensive demo seed for evaluation, testing, and immediate demonstration.
    Loads clearly-labelled 'Demo Data' for activities, user accounts (admin, teacher, parent),
    learners, educator assignments, and realistic completed sessions.
    Guarantees demo accounts have password 'DemoPass123!' and active status.
    Trains the initial K-Means pattern grouping model and generates explainable recommendations.
    """
    from datetime import datetime, timezone, timedelta
    from app.models.user import User
    from app.models.child import Child
    from app.models.teacher_assignment import TeacherAssignment
    from app.models.session import ActivitySession, InteractionEvent
    from app.services import recommendation_service
    from app.ml.model_manager import get_model_manager

    users_before = User.query.count()

    # 1. Seed Categories & Activities
    created_cats, created_acts, created_qs = seed_activities()

    # 2. Seed / Update Demo Accounts (Guarantee DemoPass123! password)
    demo_users_spec = [
        {'name': 'Administrator [Demo Data]', 'email': 'admin@childinsight.demo', 'role': 'admin', 'password': 'DemoPass123!'},
        {'name': 'Teacher Maya [Demo Data]', 'email': 'teacher@childinsight.demo', 'role': 'teacher', 'password': 'DemoPass123!'},
        {'name': 'Parent Jordan [Demo Data]', 'email': 'parent@childinsight.demo', 'role': 'parent', 'password': 'DemoPass123!'}
    ]

    users = {}
    created_users = 0
    for u_spec in demo_users_spec:
        user = User.query.filter_by(email=u_spec['email']).first()
        if not user:
            user = User(
                name=u_spec['name'],
                email=u_spec['email'],
                role=u_spec['role'],
                is_active=True
            )
            created_users += 1
        else:
            user.name = u_spec['name']
            user.role = u_spec['role']
            user.is_active = True
        user.set_password(u_spec['password'])
        db.session.add(user)
        db.session.flush()
        users[u_spec['role']] = user
    db.session.commit()

    # 3. Seed Demo Children for Parent Jordan
    parent_user = users['parent']
    demo_children_spec = [
        {'name': 'Leo [Demo Data]', 'age': 6, 'grade': '1st Grade', 'lang': 'English'},
        {'name': 'Mia [Demo Data]', 'age': 8, 'grade': '3rd Grade', 'lang': 'English'},
        {'name': 'Noah [Demo Data]', 'age': 7, 'grade': '2nd Grade', 'lang': 'English'}
    ]

    children = []
    created_children = 0
    for c_spec in demo_children_spec:
        child = Child.query.filter_by(parent_id=parent_user.id, name=c_spec['name']).first()
        if not child:
            child = Child(
                parent_id=parent_user.id,
                name=c_spec['name'],
                age=c_spec['age'],
                grade=c_spec['grade'],
                preferred_language=c_spec['lang']
            )
            db.session.add(child)
            db.session.flush()
            created_children += 1
        else:
            child.age = c_spec['age']
            child.grade = c_spec['grade']
            child.preferred_language = c_spec['lang']
            db.session.add(child)
        children.append(child)
    db.session.commit()

    # 4. Seed Teacher Assignments
    teacher_user = users['teacher']
    created_assignments = 0
    for child in children:
        existing = TeacherAssignment.query.filter_by(
            teacher_id=teacher_user.id,
            child_id=child.id
        ).first()
        if not existing:
            assignment = TeacherAssignment(teacher_id=teacher_user.id, child_id=child.id)
            db.session.add(assignment)
            created_assignments += 1
    db.session.commit()

    # 5. Seed Activity Sessions & Interaction Events
    categories = Category.query.all()
    cat_activities = {}
    for cat in categories:
        cat_activities[cat.slug] = Activity.query.filter_by(category_id=cat.id).all()

    session_plans = [
        # Leo: visual + memory strong
        (children[0], [
            ('visual', 0, 100.0, 3, 3, 4),
            ('visual', 1, 90.0, 3, 3, 3),
            ('memory', 0, 100.0, 3, 3, 3),
            ('memory', 1, 85.0, 3, 2, 2),
            ('logic', 0, 60.0, 3, 2, 1),
            ('numbers', 0, 70.0, 3, 2, 0),
        ]),
        # Mia: logic + numbers strong
        (children[1], [
            ('logic', 0, 100.0, 3, 3, 4),
            ('logic', 1, 95.0, 3, 3, 3),
            ('numbers', 0, 100.0, 3, 3, 3),
            ('numbers', 1, 90.0, 3, 3, 2),
            ('language', 0, 75.0, 3, 2, 1),
            ('visual', 0, 80.0, 3, 2, 0),
        ]),
        # Noah: balanced multi-domain
        (children[2], [
            ('visual', 0, 80.0, 3, 2, 4),
            ('memory', 0, 85.0, 3, 2, 3),
            ('language', 0, 80.0, 3, 2, 3),
            ('numbers', 0, 85.0, 3, 2, 2),
            ('logic', 0, 80.0, 3, 2, 1),
            ('visual', 1, 85.0, 3, 2, 0),
        ])
    ]

    created_sessions = 0
    now = datetime.now(timezone.utc)

    for child, plans in session_plans:
        existing_sessions = ActivitySession.query.filter_by(child_id=child.id).all()
        if fresh:
            for s in existing_sessions:
                db.session.delete(s)
            db.session.flush()
            existing_count = 0
        else:
            existing_count = len(existing_sessions)

        if existing_count < len(plans):
            for cat_slug, act_idx, accuracy, attempts, correct, days_ago in plans[existing_count:]:
                acts = cat_activities.get(cat_slug, [])
                if not acts:
                    continue
                activity = acts[min(act_idx, len(acts) - 1)]

                start_t = now - timedelta(days=days_ago, hours=2)
                end_t = start_t + timedelta(seconds=120)

                session = ActivitySession(
                    child_id=child.id,
                    activity_id=activity.id,
                    start_time=start_t,
                    end_time=end_t,
                    duration_seconds=120,
                    attempts=attempts,
                    correct_answers=correct,
                    accuracy=accuracy,
                    status=ActivitySession.STATUS_COMPLETED
                )
                db.session.add(session)
                db.session.flush()
                created_sessions += 1

                ev_start = InteractionEvent(
                    session_id=session.id,
                    child_id=child.id,
                    event_type=InteractionEvent.EVENT_STARTED,
                    timestamp=start_t
                )
                ev_answer = InteractionEvent(
                    session_id=session.id,
                    child_id=child.id,
                    event_type=InteractionEvent.EVENT_ANSWER_SELECTED,
                    timestamp=start_t + timedelta(seconds=40),
                    payload=json.dumps({'accuracy': accuracy})
                )
                ev_complete = InteractionEvent(
                    session_id=session.id,
                    child_id=child.id,
                    event_type=InteractionEvent.EVENT_COMPLETED,
                    timestamp=end_t,
                    payload=json.dumps({'score': accuracy})
                )
                db.session.add_all([ev_start, ev_answer, ev_complete])

    db.session.commit()

    # 6. Fit ML Model & Generate Recommendations
    try:
        model_mgr = get_model_manager()
        model_mgr.fit_model()
    except Exception:
        pass

    try:
        for child in children:
            recommendation_service.get_recommendations_for_child(child.id, persist=True)
    except Exception:
        pass

    users_after = User.query.count()
    demo_sessions_count = ActivitySession.query.filter(
        ActivitySession.child_id.in_([c.id for c in children])
    ).count()

    # Calculate Hindi translation coverage statistics
    all_activities = Activity.query.all()
    hindi_translated_count = 0
    english_fallback_count = 0
    category_translation_stats = {}

    for cat in Category.query.all():
        cat_acts = [a for a in all_activities if a.category_id == cat.id]
        cat_hi = 0
        cat_fallback = 0
        for act in cat_acts:
            has_hi_title = act.has_translation('hi')
            qs = ActivityQuestion.query.filter_by(activity_id=act.id).all()
            all_qs_hi = (
                len(qs) > 0 and
                all(
                    'hi' in q.translations and
                    bool(q.translations['hi'].get('question_text')) and
                    bool(q.translations['hi'].get('options')) and
                    bool(q.translations['hi'].get('correct_answer'))
                    for q in qs
                )
            )
            if has_hi_title and all_qs_hi:
                cat_hi += 1
            else:
                cat_fallback += 1
        category_translation_stats[cat.name] = {
            'hindi': cat_hi,
            'fallback': cat_fallback,
            'total': len(cat_acts)
        }
        hindi_translated_count += cat_hi
        english_fallback_count += cat_fallback

    return {
        'users_before': users_before,
        'users_after': users_after,
        'created_users': created_users,
        'total_users': users_after,
        'demo_users': [u['email'] for u in demo_users_spec],
        'created_categories': created_cats,
        'total_categories': Category.query.count(),
        'created_activities': created_acts,
        'total_activities': Activity.query.count(),
        'created_questions': created_qs,
        'total_questions': ActivityQuestion.query.count(),
        'hindi_translated_activities': hindi_translated_count,
        'english_fallback_activities': english_fallback_count,
        'category_translation_stats': category_translation_stats,
        'created_children': created_children,
        'total_children': Child.query.count(),
        'demo_children': [c['name'] for c in demo_children_spec],
        'created_sessions': created_sessions,
        'total_sessions': ActivitySession.query.count(),
        'demo_sessions': demo_sessions_count,
        # Backward compatibility aliases
        'users': created_users,
        'children': created_children,
        'assignments': created_assignments,
        'sessions': created_sessions,
        'categories': created_cats,
        'activities': created_acts,
        'questions': created_qs
    }

