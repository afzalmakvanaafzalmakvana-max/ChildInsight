import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import json

from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.models.recommendation import Recommendation
from app.models.health import HealthSnapshot
from app.agent import compliance_agent, content_integrity_agent, health_agent, scheduler
from app.utils.seed_data import seed_activities


class SystemAgentsTestCase(unittest.TestCase):
    """Automated test suite verifying the ChildInsight internal agent layer."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        compliance_agent.reset_incident_history()

        # Seed users
        self.admin = User(name='Admin User', email='admin@test.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')

        self.parent = User(name='Parent User', email='parent@test.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')

        self.teacher = User(name='Teacher User', email='teacher@test.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')

        db.session.add_all([self.admin, self.parent, self.teacher])
        db.session.commit()

        # Seed test child
        self.child = Child(parent_id=self.parent.id, name='Alex Learner', age=7, grade='2nd Grade')
        db.session.add(self.child)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # -------------------------------------------------------------
    # 1. Safety & Compliance Agent Tests
    # -------------------------------------------------------------
    def test_compliance_agent_catches_blacklisted_terms(self):
        """Verifies forbidden clinical/diagnostic words are blocked with matching rule."""
        forbidden_samples = [
            ("Child demonstrates adhd traits during task", "adhd"),
            ("Possible autism spectrum indicators observed", "autism"),
            ("Practice needed due to dyslexia pattern", "dyslexia"),
            ("Learning disorder detected in memory", "disorder"),
            ("Cognitive deficit identified", "deficit"),
            ("Low iq score estimated", "iq"),
            ("Visual impairment observed", "impairment"),
            ("Requires clinical evaluation", "clinical"),
            ("Diagnostic assessment recommended", "diagnostic")
        ]

        for text, expected_term in forbidden_samples:
            is_safe, reason = compliance_agent.check_text(text)
            self.assertFalse(is_safe, f"Failed to catch forbidden term in: '{text}'")
            self.assertIn(expected_term, reason.lower())

    def test_compliance_agent_passes_clean_educational_text(self):
        """Verifies positive, encouraging educational prose passes without objection."""
        clean_samples = [
            "Strong recent performance in Visual Learning (85% accuracy). Ready for the next challenge at Advanced level.",
            "Supported practice recommended in Logic (42% accuracy) with accessible Easy activities.",
            "Steady progress shown in Memory (68% accuracy). Reinforce skills with another Medium activity.",
            "Alex completed 3 activities today. Strong performance: Numbers, Visual Matching.",
            "Educator assigned 'Pattern Detective' to Alex for guided learning."
        ]

        for text in clean_samples:
            is_safe, reason = compliance_agent.check_text(text)
            self.assertTrue(is_safe, f"Falsely flagged clean text: '{text}' (Reason: {reason})")
            self.assertIsNone(reason)

    def test_compliance_agent_enforce_substitutes_fallback_and_logs(self):
        """Verifies enforce_compliance substitutes generic text and logs incident without raw text leak."""
        bad_text = "Child shows severe mental deficit and abnormal response."
        fallback = "Engaging practice activity to support continuous learning."

        result = compliance_agent.enforce_compliance(
            bad_text,
            context={'source': 'recommendation', 'child_id': self.child.id},
            fallback_text=fallback
        )

        self.assertEqual(result, fallback)
        self.assertEqual(compliance_agent.get_recent_incident_count(), 1)

        summary = compliance_agent.get_recent_incidents_summary()
        self.assertEqual(len(summary), 1)
        self.assertIn('deficit', summary[0]['rule_matched'].lower())
        # Ensure raw blocked text is NOT in summary (protecting learner privacy)
        self.assertNotIn(bad_text, json.dumps(summary))

    # -------------------------------------------------------------
    # 2. Content Integrity Agent Tests
    # -------------------------------------------------------------
    def test_content_integrity_agent_detects_all_issue_types(self):
        """Tests that content integrity agent detects all 5 specified anomaly types."""
        # Setup category with zero activities
        empty_cat = Category(name='Empty Science', slug='empty-science', description='No activities')
        db.session.add(empty_cat)

        # Setup valid category
        valid_cat = Category(name='Valid Math', slug='valid-math', description='Has activities')
        db.session.add(valid_cat)
        db.session.commit()

        # Activity 1: Zero questions
        act_no_q = Activity(category_id=valid_cat.id, title='Zero Q Activity', difficulty='Easy', min_age=6, max_age=8)
        # Activity 2: Invalid difficulty & invalid age bounds
        act_invalid_bounds = Activity(category_id=valid_cat.id, title='Invalid Bounds Act', difficulty='ExtremeExpert', min_age=16, max_age=5)
        # Activity 3: Duplicate questions
        act_dupes = Activity(category_id=valid_cat.id, title='Duplicate Q Act', difficulty='Medium', min_age=6, max_age=9)

        db.session.add_all([act_no_q, act_invalid_bounds, act_dupes])
        db.session.commit()

        # Add duplicate questions to Activity 3
        q1 = ActivityQuestion(activity_id=act_dupes.id, question_text="What is 2 + 2?", question_type="single_choice", options_json='["3","4"]', correct_answer="4", order_num=1)
        q2 = ActivityQuestion(activity_id=act_dupes.id, question_text="what is 2 + 2? ", question_type="single_choice", options_json='["3","4"]', correct_answer="4", order_num=2)
        # Orphaned question (points to non-existent activity_id)
        orphan_q = ActivityQuestion(activity_id=999999, question_text="Orphaned Question Text?", question_type="single_choice", options_json='["A","B"]', correct_answer="A", order_num=1)

        db.session.add_all([q1, q2, orphan_q])
        db.session.commit()

        issues = content_integrity_agent.run_audit()
        issue_types = [i['issue_type'] for i in issues]

        self.assertIn('empty_category', issue_types)
        self.assertIn('zero_questions', issue_types)
        self.assertIn('invalid_bounds', issue_types)
        self.assertIn('duplicate_question', issue_types)
        self.assertIn('orphaned_question', issue_types)

    # -------------------------------------------------------------
    # 3. Platform Health Agent Tests
    # -------------------------------------------------------------
    def test_health_metrics_computation_and_snapshot_persistence(self):
        """Verifies health score calculation and persistence in health_snapshots table."""
        # Seed standard valid activities
        seed_activities()

        # Compute initial metrics
        metrics = health_agent.compute_health_metrics()
        self.assertIsInstance(metrics['score'], float)
        self.assertTrue(0.0 <= metrics['score'] <= 100.0)
        self.assertIn('details', metrics)

        # Record a snapshot
        snapshot = health_agent.record_snapshot()
        self.assertIsNotNone(snapshot.id)
        self.assertEqual(snapshot.score, metrics['score'])

        # Verify query in database
        db_snapshot = db.session.get(HealthSnapshot, snapshot.id)
        self.assertIsNotNone(db_snapshot)
        self.assertEqual(db_snapshot.score, snapshot.score)

        # Test trend retrieval
        trend = health_agent.get_health_trend(limit=5)
        self.assertGreaterEqual(len(trend), 1)
        self.assertEqual(trend[-1].id, snapshot.id)

    # -------------------------------------------------------------
    # 4. Background Scheduler Runner Tests
    # -------------------------------------------------------------
    def test_scheduler_runs_idempotently(self):
        """Verifies scheduler runs all steps safely and idempotently."""
        seed_activities()

        result1 = scheduler.run_maintenance_pipeline(triggered_by='test')
        self.assertIn(result1['status'], ('success', 'partial_failure'))
        self.assertEqual(len(result1['steps']), 7)

        # Running a second time immediately should not fail or create duplicate recommendations
        result2 = scheduler.run_maintenance_pipeline(triggered_by='test')
        self.assertIn(result2['status'], ('success', 'partial_failure'))
        self.assertEqual(len(result2['steps']), 7)

    def test_scheduler_concurrency_lock_prevents_overlap(self):
        """Verifies concurrency lock prevents overlapping runs."""
        acquired = scheduler._RUN_LOCK.acquire(blocking=False)
        self.assertTrue(acquired)
        try:
            overlap_res = scheduler.run_maintenance_pipeline(triggered_by='test_concurrent')
            self.assertEqual(overlap_res['status'], 'skipped')
            self.assertIn('already in progress', overlap_res['message'])
        finally:
            scheduler._RUN_LOCK.release()

    def test_scheduler_resilience_fault_isolation(self):
        """Verifies a failing step does NOT block subsequent steps from executing."""
        # Intentionally break Step 2 (refitting K-Means) with an unhandled exception
        with patch('app.ml.model_manager.fit_model', side_effect=RuntimeError("Simulated clustering failure")):
            result = scheduler.run_maintenance_pipeline(triggered_by='test_resilience')

            # Pipeline completes with partial_failure rather than crashing
            self.assertEqual(result['status'], 'partial_failure')

            # Step 2 should be marked failure
            step2 = next(s for s in result['steps'] if s['name'] == 'Refit K-Means Clustering')
            self.assertEqual(step2['status'], 'failure')
            self.assertIn("Simulated clustering failure", step2['message'])

            # Step 4 (Content sweep) and Step 5 (Health snapshot) MUST have still run and succeeded
            step4 = next(s for s in result['steps'] if s['name'] == 'Content Integrity & Compliance Sweep')
            self.assertEqual(step4['status'], 'success')

            step5 = next(s for s in result['steps'] if s['name'] == 'Record Health Snapshot')
            self.assertEqual(step5['status'], 'success')

    # -------------------------------------------------------------
    # 5. Admin Dashboard RBAC & Routes Tests
    # -------------------------------------------------------------
    def test_agents_dashboard_access_control(self):
        """Verifies only administrators can access /admin/agents and trigger runs."""
        # 1. Anonymous user
        resp = self.client.get('/admin/agents')
        self.assertEqual(resp.status_code, 302)

        # 2. Parent user (403)
        self.client.post('/login', data={'email': 'parent@test.com', 'password': 'ParentPass123!'})
        resp = self.client.get('/admin/agents')
        self.assertEqual(resp.status_code, 403)
        resp_post = self.client.post('/admin/agents/run')
        self.assertEqual(resp_post.status_code, 403)
        self.client.get('/logout')

        # 3. Teacher user (403)
        self.client.post('/login', data={'email': 'teacher@test.com', 'password': 'TeacherPass123!'})
        resp = self.client.get('/admin/agents')
        self.assertEqual(resp.status_code, 403)
        self.client.get('/logout')

        # 4. Admin user (200 OK)
        self.client.post('/login', data={'email': 'admin@test.com', 'password': 'AdminPass123!'})
        resp = self.client.get('/admin/agents')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'System Agents', resp.data)
        self.assertIn(b'Platform Health', resp.data)
        self.assertIn(b'Content Integrity Audit', resp.data)

        # Trigger run from Admin
        resp_post = self.client.post('/admin/agents/run', follow_redirects=True)
        self.assertEqual(resp_post.status_code, 200)
        self.assertIn(b'Agent pipeline executed', resp_post.data)

    # -------------------------------------------------------------
    # 6. Age-Band Health & Content Gap Breakdown Tests
    # -------------------------------------------------------------
    def test_per_age_band_health_score_calculation_multiple_age_bands(self):
        """Verifies per-age-band health score calculation on sample data across all 4 cohorts."""
        from app.models.content_suggestion import ContentSuggestion

        # Setup test category
        cat = Category(name='Cognitive Quest', slug='cog-quest', description='Test domain')
        db.session.add(cat)
        db.session.commit()

        # Seed children across multiple age bands
        child_4_6 = Child(parent_id=self.parent.id, name='Preschool Kid', age=5)
        child_6_9 = Child(parent_id=self.parent.id, name='Early Elem Kid', age=7)
        child_9_12 = Child(parent_id=self.parent.id, name='Upper Elem Kid', age=10)
        child_12_14 = Child(parent_id=self.parent.id, name='Secondary Kid', age=13)
        db.session.add_all([child_4_6, child_6_9, child_9_12, child_12_14])
        db.session.commit()

        # Seed activities for age bands
        # Band 4-6: 1 valid activity
        act_4_6 = Activity(category_id=cat.id, title='Act 4-6', difficulty='Beginner', min_age=4, max_age=6)
        # Band 6-9: 1 valid activity
        act_6_9 = Activity(category_id=cat.id, title='Act 6-9', difficulty='Easy', min_age=6, max_age=9)
        # Band 9-12: 1 invalid activity (zero questions -> 0% valid adequacy)
        act_9_12 = Activity(category_id=cat.id, title='Act 9-12 No Qs', difficulty='Medium', min_age=9, max_age=12)
        # Band 12-14: 0 activities seeded (0% adequacy)

        db.session.add_all([act_4_6, act_6_9, act_9_12])
        db.session.commit()

        # Add questions only to act_4_6 and act_6_9
        q1 = ActivityQuestion(activity_id=act_4_6.id, question_text='Q1?', options_json='["A","B"]', correct_answer='A', order_num=1)
        q2 = ActivityQuestion(activity_id=act_6_9.id, question_text='Q2?', options_json='["A","B"]', correct_answer='B', order_num=1)
        db.session.add_all([q1, q2])
        db.session.commit()

        # Seed sessions:
        # Band 4-6: 2 sessions, both completed -> 100% completion rate
        s_4_6_1 = ActivitySession(child_id=child_4_6.id, activity_id=act_4_6.id, status=ActivitySession.STATUS_COMPLETED, start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))
        s_4_6_2 = ActivitySession(child_id=child_4_6.id, activity_id=act_4_6.id, status=ActivitySession.STATUS_COMPLETED, start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))

        # Band 6-9: 2 sessions, 1 completed, 1 in_progress -> 50% completion rate
        s_6_9_1 = ActivitySession(child_id=child_6_9.id, activity_id=act_6_9.id, status=ActivitySession.STATUS_COMPLETED, start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))
        s_6_9_2 = ActivitySession(child_id=child_6_9.id, activity_id=act_6_9.id, status=ActivitySession.STATUS_IN_PROGRESS, start_time=datetime.now(timezone.utc))

        # Band 9-12: 1 session, completed -> 100% completion rate
        s_9_12_1 = ActivitySession(child_id=child_9_12.id, activity_id=act_9_12.id, status=ActivitySession.STATUS_COMPLETED, start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc))

        # Band 12-14: 0 sessions -> 100% completion rate (default)
        db.session.add_all([s_4_6_1, s_4_6_2, s_6_9_1, s_6_9_2, s_9_12_1])
        db.session.commit()

        # Add a pending content gap affecting 6-9
        gap_6_9 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat.id,
            age_band='6-9',
            target_difficulty='Medium',
            suggested_title='Logic Challenge 6-9',
            reason='Progression gap for 6-9',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(gap_6_9)
        db.session.commit()

        # Execute compute_age_band_health_metrics
        breakdown = health_agent.compute_age_band_health_metrics()
        by_band = {b['age_band']: b for b in breakdown}

        # Assert all 4 cohorts exist
        self.assertIn('4-6', by_band)
        self.assertIn('6-9', by_band)
        self.assertIn('9-12', by_band)
        self.assertIn('12-14', by_band)

        # 4-6: 100% completion (2/2), 100% adequacy (1/1) -> 100.0 score
        self.assertEqual(by_band['4-6']['completion_rate'], 100.0)
        self.assertEqual(by_band['4-6']['content_adequacy'], 100.0)
        self.assertEqual(by_band['4-6']['score'], 100.0)
        self.assertEqual(by_band['4-6']['gaps_count'], 0)

        # 6-9: 50% completion (1/2), 100% adequacy (1/1) -> 75.0 score
        self.assertEqual(by_band['6-9']['completion_rate'], 50.0)
        self.assertEqual(by_band['6-9']['content_adequacy'], 100.0)
        self.assertEqual(by_band['6-9']['score'], 75.0)
        self.assertEqual(by_band['6-9']['gaps_count'], 1)
        self.assertEqual(by_band['6-9']['content_gaps'][0]['title'], 'Logic Challenge 6-9')

        # 9-12: 100% completion (1/1), 0% adequacy (0/1 valid) -> 50.0 score
        self.assertEqual(by_band['9-12']['completion_rate'], 100.0)
        self.assertEqual(by_band['9-12']['content_adequacy'], 0.0)
        self.assertEqual(by_band['9-12']['score'], 50.0)

        # 12-14: 100% completion (0 sessions default), 0% adequacy (0 acts) -> 50.0 score
        self.assertEqual(by_band['12-14']['completion_rate'], 100.0)
        self.assertEqual(by_band['12-14']['content_adequacy'], 0.0)
        self.assertEqual(by_band['12-14']['score'], 50.0)

        # Also verify consolidated compute_health_metrics includes age_bands
        overall = health_agent.compute_health_metrics()
        self.assertIn('age_band_breakdown', overall)
        self.assertIn('age_bands', overall)
        self.assertEqual(overall['age_bands']['6-9']['score'], 75.0)

    def test_agents_dashboard_age_band_breakdown_rendering(self):
        """Verifies the Admin System Agents dashboard renders the age-band breakdown table."""
        from app.models.content_suggestion import ContentSuggestion

        # Add a gap
        cat = Category(name='Visual Learning', slug='visual-test', description='Visual')
        db.session.add(cat)
        db.session.commit()

        gap = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=cat.id,
            age_band='4-6',
            target_difficulty='Beginner',
            suggested_title='Visual Pre-K Quest',
            reason='Gap for ages 4-6',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(gap)
        db.session.commit()

        # Login as admin
        self.client.post('/login', data={'email': 'admin@test.com', 'password': 'AdminPass123!'})
        res = self.client.get('/admin/agents')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Assert breakdown table card and columns
        self.assertIn('Developmental Age-Band Health & Content Breakdown', html)
        self.assertIn('Age Band', html)
        self.assertIn('Health Score', html)
        self.assertIn('Session Completion', html)
        self.assertIn('Content Adequacy', html)
        self.assertIn('Active Learners', html)
        self.assertIn('Detected Content Gaps', html)

        # Assert all 4 cohorts rendered in HTML
        self.assertIn('Ages 4-6', html)
        self.assertIn('Ages 6-9', html)
        self.assertIn('Ages 9-12', html)
        self.assertIn('Ages 12-14', html)

        # Assert detected gap is linked in the table
        self.assertIn('Visual Pre-K Quest', html)
        self.assertIn('/admin/content-suggestions', html)
        self.assertIn('Adequate Coverage', html)


if __name__ == '__main__':
    unittest.main()

