import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort, jsonify, g
from flask_login import login_required, current_user
from app import db
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.services import event_tracker
from app.translations import normalize_language, translate

child_bp = Blueprint('child', __name__)


def get_authorized_child(child_id):
    """Enforce that only the child (or their parent/admin) can access their activity space."""
    child = db.session.get(Child, child_id)
    if not child:
        abort(404)

    # Set active child language context for templates and i18n
    g.child_lang = normalize_language(child.preferred_language)

    if current_user.is_admin:
        return child
    if current_user.is_parent and child.parent_id == current_user.id:
        return child
    if current_user.is_child and current_user.id == child.id:
        return child

    abort(403)


@child_bp.route('/home')
def home():
    """Child entry hub; selects active child profile if logged in as parent."""
    categories = Category.query.order_by(Category.id).all()
    categories_by_slug = {c.slug: c for c in categories}

    child_id = request.args.get('child_id', type=int)
    if child_id:
        child = db.session.get(Child, child_id)
        if child:
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=url_for('child.categories_hub', child_id=child.id)))
            if current_user.is_admin or (current_user.is_parent and child.parent_id == current_user.id) or (current_user.is_child and current_user.id == child.id):
                return redirect(url_for('child.categories_hub', child_id=child.id))

    if not current_user.is_authenticated:
        return render_template('base_child.html', categories=categories, categories_by_slug=categories_by_slug, child=None, child_lang='en')

    if current_user.is_parent:
        children = Child.query.filter_by(parent_id=current_user.id).all()
        if len(children) == 1:
            return redirect(url_for('child.categories_hub', child_id=children[0].id))
        if len(children) > 1:
            return render_template('child/select_child.html', children=children)
        flash("Please add a child profile first.", "info")
        return redirect(url_for('parent.dashboard'))

    if current_user.is_child:
        child = Child.query.filter_by(id=current_user.id).first()
        if child:
            return redirect(url_for('child.categories_hub', child_id=child.id))

    if current_user.is_teacher:
        return redirect(url_for('teacher.dashboard'))

    return render_template('base_child.html', categories=categories, categories_by_slug=categories_by_slug, child=None, child_lang='en')



@child_bp.route('/<int:child_id>/activities')
@login_required
def categories_hub(child_id):
    """Category selector displaying 5 big colorful activity domains."""
    child = get_authorized_child(child_id)
    categories = Category.query.order_by(Category.id).all()
    child_lang = getattr(g, 'child_lang', 'en')
    return render_template('child/activities.html', child=child, categories=categories, child_lang=child_lang)


@child_bp.route('/<int:child_id>/category/<int:category_id>')
@login_required
def activity_list(child_id, category_id):
    """Activity picker showing difficulty levels for a chosen category."""
    child = get_authorized_child(child_id)
    category = db.session.get(Category, category_id)
    if not category:
        abort(404)

    query = Activity.query.filter(
        Activity.category_id == category.id,
        Activity.is_active.is_(True)
    )
    if child.age is not None:
        query = query.filter(
            Activity.min_age <= child.age,
            Activity.max_age >= child.age
        )
    activities = query.order_by(Activity.min_age, Activity.id).all()
    child_lang = getattr(g, 'child_lang', 'en')
    return render_template('child/activity_list.html', child=child, category=category, activities=activities, child_lang=child_lang)


@child_bp.route('/<int:child_id>/play/<int:activity_id>')
@login_required
def player(child_id, activity_id):
    """Interactive question-by-question activity player with real-time event tracking."""
    child = get_authorized_child(child_id)
    activity = db.session.get(Activity, activity_id)
    if not activity:
        abort(404)

    child_lang = getattr(g, 'child_lang', 'en')

    questions = activity.questions.order_by(ActivityQuestion.order_num).all()
    if not questions:
        flash("No questions available for this activity yet.", "info")
        return redirect(url_for('child.activity_list', child_id=child.id, category_id=activity.category_id))

    q_idx = request.args.get('q', default=0, type=int)

    # Initialize or resume session and play state
    state = session.get('play_state', {})
    if q_idx == 0 or state.get('activity_id') != activity.id or state.get('child_id') != child.id:
        act_session = event_tracker.start_session(child_id=child.id, activity_id=activity.id)
        state = {
            'session_id': act_session.id,
            'child_id': child.id,
            'activity_id': activity.id,
            'current_q': 0,
            'total_q': len(questions),
            'score': 0
        }
        session['play_state'] = state
    else:
        session_id = state.get('session_id')
        act_session = db.session.get(ActivitySession, session_id) if session_id else None
        if not act_session or act_session.status != ActivitySession.STATUS_IN_PROGRESS:
            act_session = event_tracker.start_session(child_id=child.id, activity_id=activity.id)
            state['session_id'] = act_session.id
            session['play_state'] = state

    if q_idx >= len(questions):
        return redirect(url_for('child.results', child_id=child.id, activity_id=activity.id))

    current_question = questions[q_idx]

    # Display options in randomized order on render for child's preferred language
    display_options = current_question.get_shuffled_options(child_lang)

    # Log question viewed event
    event_tracker.log_question_viewed(
        session_id=act_session.id,
        child_id=child.id,
        question_id=current_question.id,
        q_idx=q_idx
    )

    return render_template(
        'child/player.html',
        child=child,
        activity=activity,
        question=current_question,
        options=display_options,
        q_idx=q_idx,
        total_q=len(questions),
        feedback=None,
        child_lang=child_lang
    )


@child_bp.route('/<int:child_id>/play/<int:activity_id>/answer', methods=['POST'])
@login_required
def answer(child_id, activity_id):
    """Evaluates answer, logs interaction events, and renders feedback."""
    child = get_authorized_child(child_id)
    activity = db.session.get(Activity, activity_id)
    if not activity:
        abort(404)

    child_lang = getattr(g, 'child_lang', 'en')

    question_id = request.form.get('question_id', type=int)
    selected_answer = request.form.get('selected_answer', '').strip()
    q_idx = request.form.get('q_idx', default=0, type=int)

    # Server-side input validation per rules.md §4
    if not question_id or question_id <= 0 or not selected_answer or len(selected_answer) > 255 or q_idx < 0:
        abort(400)

    question = db.session.get(ActivityQuestion, question_id)
    if not question or question.activity_id != activity.id:
        abort(400)

    questions = activity.questions.order_by(ActivityQuestion.order_num).all()
    state = session.get('play_state', {})
    session_id = state.get('session_id')

    if not session_id:
        act_session = ActivitySession.query.filter_by(
            child_id=child.id,
            activity_id=activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).order_by(ActivitySession.id.desc()).first()
        if not act_session:
            act_session = event_tracker.start_session(child_id=child.id, activity_id=activity.id)
        session_id = act_session.id
        state['session_id'] = session_id

    expected_ans = question.get_correct_answer(child_lang).strip()
    is_correct = (
        selected_answer.lower() == expected_ans.lower()
        or selected_answer.lower() == question.correct_answer.strip().lower()
    )

    # Record answer in real time through event tracker
    act_session, _ = event_tracker.record_answer(
        session_id=session_id,
        child_id=child.id,
        question_id=question.id,
        selected_answer=selected_answer,
        is_correct=is_correct
    )

    state['child_id'] = child.id
    state['activity_id'] = activity.id
    state['current_q'] = q_idx + 1
    state['total_q'] = len(questions)
    state['score'] = act_session.correct_answers if act_session else state.get('score', 0) + (1 if is_correct else 0)
    session['play_state'] = state

    is_last = (q_idx + 1 >= len(questions))
    feedback_message = (
        translate('feedback_correct', lang=child_lang) if is_correct
        else translate('feedback_incorrect', lang=child_lang, answer=expected_ans)
    )

    feedback = {
        'is_correct': is_correct,
        'selected': selected_answer,
        'correct_answer': expected_ans,
        'message': feedback_message,
        'next_q_idx': q_idx + 1,
        'is_last': is_last
    }

    return render_template(
        'child/player.html',
        child=child,
        activity=activity,
        question=question,
        q_idx=q_idx,
        total_q=len(questions),
        feedback=feedback,
        child_lang=child_lang
    )


@child_bp.route('/<int:child_id>/play/<int:activity_id>/hint', methods=['POST'])
@login_required
def hint(child_id, activity_id):
    """Tracks hint usage for learning assistance analytics."""
    child = get_authorized_child(child_id)
    question_id = request.form.get('question_id', type=int) or request.args.get('question_id', type=int)
    if not question_id or question_id <= 0:
        abort(400)

    question = db.session.get(ActivityQuestion, question_id)
    if not question or question.activity_id != activity_id:
        abort(400)

    state = session.get('play_state', {})
    session_id = state.get('session_id')
    if session_id and question:
        event_tracker.log_hint_used(session_id=session_id, child_id=child.id, question_id=question.id)

    child_lang = getattr(g, 'child_lang', 'en')
    hint_text = question.get_hint(child_lang) if question else ''

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'ok', 'hint': hint_text})

    flash(f"💡 Hint: {hint_text or 'Look closely at the clues!'}", "info")
    q_idx = request.form.get('q_idx', default=0, type=int)
    return redirect(url_for('child.player', child_id=child.id, activity_id=activity_id, q=q_idx))


@child_bp.route('/<int:child_id>/play/<int:activity_id>/skip', methods=['POST'])
@login_required
def skip(child_id, activity_id):
    """Allows child to skip a question gracefully, logging the event."""
    child = get_authorized_child(child_id)
    activity = db.session.get(Activity, activity_id)
    if not activity:
        abort(404)

    question_id = request.form.get('question_id', type=int)
    q_idx = request.form.get('q_idx', default=0, type=int)

    if not question_id or question_id <= 0 or q_idx < 0:
        abort(400)

    question = db.session.get(ActivityQuestion, question_id)
    if not question or question.activity_id != activity.id:
        abort(400)

    state = session.get('play_state', {})
    session_id = state.get('session_id')
    if session_id and question_id:
        event_tracker.log_question_skipped(session_id=session_id, child_id=child.id, question_id=question_id)

    questions_count = activity.questions.count()
    next_q = q_idx + 1
    state['current_q'] = next_q
    session['play_state'] = state

    if next_q >= questions_count:
        return redirect(url_for('child.results', child_id=child.id, activity_id=activity.id))
    return redirect(url_for('child.player', child_id=child.id, activity_id=activity.id, q=next_q))


@child_bp.route('/<int:child_id>/play/<int:activity_id>/abandon', methods=['GET', 'POST'])
@login_required
def abandon(child_id, activity_id):
    """Handles early exit from an activity and records abandonment."""
    child = get_authorized_child(child_id)
    activity = db.session.get(Activity, activity_id)
    if not activity:
        abort(404)

    state = session.pop('play_state', {})
    session_id = state.get('session_id')
    if not session_id:
        act_session = ActivitySession.query.filter_by(
            child_id=child.id,
            activity_id=activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).order_by(ActivitySession.id.desc()).first()
        if act_session:
            session_id = act_session.id

    if session_id:
        event_tracker.abandon_session(session_id=session_id, child_id=child.id, reason='user_exit')

    return redirect(url_for('child.activity_list', child_id=child.id, category_id=activity.category_id))


@child_bp.route('/<int:child_id>/play/<int:activity_id>/results')
@login_required
def results(child_id, activity_id):
    """Finalizes session, logs completion event, and shows positive completion screen."""
    child = get_authorized_child(child_id)
    activity = db.session.get(Activity, activity_id)
    if not activity:
        abort(404)

    state = session.pop('play_state', {})
    session_id = state.get('session_id')
    if not session_id:
        act_session = ActivitySession.query.filter_by(
            child_id=child.id,
            activity_id=activity.id,
            status=ActivitySession.STATUS_IN_PROGRESS
        ).order_by(ActivitySession.id.desc()).first()
        if act_session:
            session_id = act_session.id

    if session_id:
        act_session = event_tracker.complete_session(session_id=session_id, child_id=child.id)
        score = act_session.correct_answers
        total_q = act_session.attempts if act_session.attempts > 0 else activity.questions.count()
    else:
        score = state.get('score', 0)
        total_q = state.get('total_q', activity.questions.count() or 3)

    child_lang = getattr(g, 'child_lang', 'en')
    return render_template(
        'child/results.html',
        child=child,
        activity=activity,
        score=score,
        total_q=total_q,
        child_lang=child_lang
    )
