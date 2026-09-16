from datetime import datetime, timezone
import logging
import threading
import time
from app import db
from app.models.child import Child
from app.models.session import ActivitySession
from app.models.progress import ProgressRecord
from app.models.recommendation import Recommendation
from app.services import analytics_service, recommendation_service
from app.ml import model_manager
from app.agent import compliance_agent, content_integrity_agent, content_suggestion_agent, health_agent

logger = logging.getLogger('childinsight.scheduler')

_RUN_LOCK = threading.Lock()

_LAST_RUN_STATE = {
    'last_run_time': None,
    'duration_seconds': 0.0,
    'triggered_by': None,
    'status': 'idle',
    'is_running': False,
    'health_score': None,
    'steps': []
}


def get_last_run_status() -> dict:
    """Returns a snapshot copy of the last execution state."""
    return dict(_LAST_RUN_STATE)


def run_maintenance_pipeline(triggered_by: str = 'scheduler') -> dict:
    """
    Executes the sequential, idempotent internal maintenance pipeline.
    Steps:
    1. Refresh progress records for children with recent activity sessions
    2. Refit K-Means interaction clustering model if enough data exists
    3. Regenerate personalized recommendations for children with new sessions
    4. Run content integrity + compliance sweep
    5. Generate adaptive content suggestions based on learner demographics and gaps
    6. Record platform health snapshot

    Uses a concurrency lock to prevent overlapping runs.
    Each step is isolated in its own try/except block so a failure in one step
    never blocks subsequent steps.
    """
    acquired = _RUN_LOCK.acquire(blocking=False)
    if not acquired:
        logger.warning("Agent maintenance run skipped: a run is already in progress.")
        return {
            'status': 'skipped',
            'message': 'A maintenance run is already in progress.',
            'triggered_by': triggered_by,
            'steps': []
        }

    start_time = time.time()
    now_utc = datetime.now(timezone.utc)
    steps_results = []
    overall_status = 'success'

    _LAST_RUN_STATE['is_running'] = True
    _LAST_RUN_STATE['triggered_by'] = triggered_by

    try:
        # -------------------------------------------------------------
        # Step 1: Refresh Progress Records
        # -------------------------------------------------------------
        step_start = time.time()
        try:
            children_with_sessions = Child.query.join(ActivitySession).distinct().all()
            updated_count = 0
            for child in children_with_sessions:
                latest_session = (
                    ActivitySession.query.filter_by(child_id=child.id)
                    .order_by(ActivitySession.end_time.desc())
                    .first()
                )
                latest_progress = (
                    ProgressRecord.query.filter_by(child_id=child.id)
                    .order_by(ProgressRecord.recorded_at.desc())
                    .first()
                )

                # Only refresh if child has new session activity since last progress record
                should_refresh = False
                if not latest_progress:
                    should_refresh = True
                elif latest_session and latest_session.end_time and latest_session.end_time > latest_progress.recorded_at:
                    should_refresh = True

                if should_refresh:
                    analytics_service.update_child_progress_records(child.id)
                    updated_count += 1

            steps_results.append({
                'name': 'Refresh Progress Records',
                'status': 'success',
                'message': f"Refreshed progress records for {updated_count} active learner(s).",
                'duration': round(time.time() - step_start, 3)
            })
        except Exception as e:
            logger.exception("Step 1 failed in maintenance pipeline: %s", str(e))
            overall_status = 'partial_failure'
            steps_results.append({
                'name': 'Refresh Progress Records',
                'status': 'failure',
                'message': f"Error refreshing progress: {str(e)}",
                'duration': round(time.time() - step_start, 3)
            })

        # -------------------------------------------------------------
        # Step 2: Refit K-Means Model
        # -------------------------------------------------------------
        step_start = time.time()
        try:
            fit_result = model_manager.fit_model()
            if fit_result.get('status') == 'success':
                msg = f"K-Means refitted successfully with {fit_result.get('n_clusters')} clusters."
                step_status = 'success'
            else:
                msg = f"Clustering skipped ({fit_result.get('message', 'cold start')})."
                step_status = 'skipped'

            steps_results.append({
                'name': 'Refit K-Means Clustering',
                'status': step_status,
                'message': msg,
                'duration': round(time.time() - step_start, 3)
            })
        except Exception as e:
            logger.exception("Step 2 failed in maintenance pipeline: %s", str(e))
            overall_status = 'partial_failure'
            steps_results.append({
                'name': 'Refit K-Means Clustering',
                'status': 'failure',
                'message': f"Error refitting K-Means: {str(e)}",
                'duration': round(time.time() - step_start, 3)
            })

        # -------------------------------------------------------------
        # Step 3: Regenerate Recommendations
        # -------------------------------------------------------------
        step_start = time.time()
        try:
            all_children = Child.query.all()
            recs_refreshed = 0
            for child in all_children:
                latest_session = (
                    ActivitySession.query.filter_by(child_id=child.id)
                    .order_by(ActivitySession.end_time.desc())
                    .first()
                )
                latest_rec = (
                    Recommendation.query.filter_by(child_id=child.id)
                    .order_by(Recommendation.created_at.desc())
                    .first()
                )

                needs_recs = False
                if not latest_rec:
                    needs_recs = True
                elif latest_session and latest_session.end_time and latest_session.end_time > latest_rec.created_at:
                    needs_recs = True

                if needs_recs:
                    recommendation_service.generate_personalized_recommendations(child.id, persist=True)
                    recs_refreshed += 1

            steps_results.append({
                'name': 'Regenerate Recommendations',
                'status': 'success',
                'message': f"Regenerated recommendations for {recs_refreshed} learner(s).",
                'duration': round(time.time() - step_start, 3)
            })
        except Exception as e:
            logger.exception("Step 3 failed in maintenance pipeline: %s", str(e))
            overall_status = 'partial_failure'
            steps_results.append({
                'name': 'Regenerate Recommendations',
                'status': 'failure',
                'message': f"Error regenerating recommendations: {str(e)}",
                'duration': round(time.time() - step_start, 3)
            })

        # -------------------------------------------------------------
        # Step 4: Content Integrity + Compliance Sweep
        # -------------------------------------------------------------
        step_start = time.time()
        try:
            issues = content_integrity_agent.run_audit()
            recent_incidents = compliance_agent.get_recent_incident_count(since_hours=24)
            msg = f"Audit complete: {len(issues)} integrity issue(s), {recent_incidents} recent compliance incident(s)."
            steps_results.append({
                'name': 'Content Integrity & Compliance Sweep',
                'status': 'success',
                'message': msg,
                'duration': round(time.time() - step_start, 3)
            })
        except Exception as e:
            logger.exception("Step 4 failed in maintenance pipeline: %s", str(e))
            overall_status = 'partial_failure'
            steps_results.append({
                'name': 'Content Integrity & Compliance Sweep',
                'status': 'failure',
                'message': f"Error running content sweep: {str(e)}",
                'duration': round(time.time() - step_start, 3)
            })

        # -------------------------------------------------------------
        # Step 5: Adaptive Content Suggestions
        # -------------------------------------------------------------
        step_start = time.time()
        try:
            suggestions = content_suggestion_agent.generate_suggestions(persist=True)
            msg = f"Generated/updated {len(suggestions)} content suggestion(s)."
            steps_results.append({
                'name': 'Adaptive Content Suggestions',
                'status': 'success',
                'message': msg,
                'duration': round(time.time() - step_start, 3)
            })
        except Exception as e:
            logger.exception("Step 5 failed in maintenance pipeline: %s", str(e))
            overall_status = 'partial_failure'
            steps_results.append({
                'name': 'Adaptive Content Suggestions',
                'status': 'failure',
                'message': f"Error generating content suggestions: {str(e)}",
                'duration': round(time.time() - step_start, 3)
            })

        # -------------------------------------------------------------
        # Step 6: Record Health Snapshot
        # -------------------------------------------------------------
        step_start = time.time()
        current_score = None
        try:
            snapshot = health_agent.record_snapshot()
            current_score = snapshot.score
            steps_results.append({
                'name': 'Record Health Snapshot',
                'status': 'success',
                'message': f"Health snapshot recorded (Score: {snapshot.score}/100).",
                'duration': round(time.time() - step_start, 3)
            })
        except Exception as e:
            logger.exception("Step 6 failed in maintenance pipeline: %s", str(e))
            overall_status = 'partial_failure'
            steps_results.append({
                'name': 'Record Health Snapshot',
                'status': 'failure',
                'message': f"Error recording health snapshot: {str(e)}",
                'duration': round(time.time() - step_start, 3)
            })

    finally:
        total_duration = round(time.time() - start_time, 3)
        _RUN_LOCK.release()

        _LAST_RUN_STATE['last_run_time'] = now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
        _LAST_RUN_STATE['duration_seconds'] = total_duration
        _LAST_RUN_STATE['status'] = overall_status
        _LAST_RUN_STATE['is_running'] = False
        _LAST_RUN_STATE['health_score'] = current_score
        _LAST_RUN_STATE['steps'] = steps_results

    return {
        'status': overall_status,
        'last_run_time': _LAST_RUN_STATE['last_run_time'],
        'duration_seconds': total_duration,
        'triggered_by': triggered_by,
        'health_score': current_score,
        'steps': steps_results
    }


def register_cli_commands(app):
    """Registers Flask CLI maintenance commands."""
    @app.cli.command('run-agents')
    def run_agents_cmd():
        """Runs the internal ChildInsight maintenance agent pipeline."""
        print("Starting ChildInsight internal agent maintenance pipeline...")
        result = run_maintenance_pipeline(triggered_by='cli')
        print(f"Completed with status: {result['status'].upper()} (Duration: {result['duration_seconds']}s)")
        if result.get('health_score') is not None:
            print(f"Platform Health Score: {result['health_score']}/100")
        print("\nStep Summary:")
        for step in result.get('steps', []):
            print(f"  [{step['status'].upper():7s}] {step['name']}: {step['message']} ({step['duration']}s)")
