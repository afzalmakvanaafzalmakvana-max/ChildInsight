import unittest
from datetime import datetime, timezone
import pandas as pd
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.teacher_assignment import TeacherAssignment
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession, InteractionEvent
from app.models.progress import ProgressRecord
from app.utils.seed_data import seed_activities
from app.services import analytics_service, engagement_service


class Phase5AnalyticsTestCase(unittest.TestCase):
    """Automated test suite verifying Phase 5 Analytics, Engagement Index, and Progress Records."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed test users
        self.parent_a = User(name='Parent A', email='parent_a@example.com', role='parent')
        self.parent_a.set_password('Pass123!')

        self.parent_b = User(name='Parent B', email='parent_b@example.com', role='parent')
        self.parent_b.set_password('Pass123!')

        self.teacher_1 = User(name='Teacher One', email='teacher_1@example.com', role='teacher')
        self.teacher_1.set_password('Pass123!')

        self.teacher_2 = User(name='Teacher Two', email='teacher_2@example.com', role='teacher')
        self.teacher_2.set_password('Pass123!')

        db.session.add_all([self.parent_a, self.parent_b, self.teacher_1, self.teacher_2])
        db.session.commit()

        # Children
        self.child_a = Child(parent_id=self.parent_a.id, name='Timmy', age=6, grade='1st Grade', preferred_language='English')
        self.child_b = Child(parent_id=self.parent_b.id, name='Sara', age=7, grade='2nd Grade', preferred_language='English')
        db.session.add_all([self.child_a, self.child_b])
        db.session.commit()

        # Assign teacher 1 to child a
        assignment = TeacherAssignment(teacher_id=self.teacher_1.id, child_id=self.child_a.id)
        db.session.add(assignment)
        db.session.commit()

        # Seed categories and activities
        seed_activities()
        self.categories = {cat.slug: cat for cat in Category.query.all()}
        self.activities = {cat.slug: Activity.query.filter_by(category_id=cat.id).all() for cat in self.categories.values()}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Pass123!'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # --- 1. Accuracy, Completion, Consistency on Known Data ---

    def test_overall_accuracy_calculation_on_known_data(self):
        """Verify weighted overall accuracy matches total_correct / total_attempts."""
        visual_act = self.activities['visual'][0]
        # Session 1: 4 attempts, 3 correct (75%)
        s1 = ActivitySession(
            child_id=self.child_a.id,
            activity_id=visual_act.id,
            attempts=4,
            correct_answers=3,
            accuracy=75.0,
            status='completed'
        )
        # Session 2: 2 attempts, 1 correct (50%)
        s2 = ActivitySession(
            child_id=self.child_a.id,
            activity_id=visual_act.id,
            attempts=2,
            correct_answers=1,
            accuracy=50.0,
            status='completed'
        )
        db.session.add_all([s1, s2])
        db.session.commit()

        df = analytics_service.load_child_session_dataframe(self.child_a.id)
        # Total: 6 attempts, 4 correct -> 4/6 * 100 = 66.67%
        acc = analytics_service.compute_overall_accuracy(df)
        self.assertEqual(acc, 66.67)

    def test_completion_rate_on_known_data(self):
        """Verify completion rate correctly computes completed vs abandoned/in_progress."""
        act = self.activities['logic'][0]
        # 3 completed, 1 abandoned -> 3/4 = 75.0%
        s1 = ActivitySession(child_id=self.child_a.id, activity_id=act.id, status='completed')
        s2 = ActivitySession(child_id=self.child_a.id, activity_id=act.id, status='completed')
        s3 = ActivitySession(child_id=self.child_a.id, activity_id=act.id, status='completed')
        s4 = ActivitySession(child_id=self.child_a.id, activity_id=act.id, status='abandoned')
        db.session.add_all([s1, s2, s3, s4])
        db.session.commit()

        df = analytics_service.load_child_session_dataframe(self.child_a.id)
        comp_rate = analytics_service.compute_completion_rate(df)
        self.assertEqual(comp_rate, 75.0)

    def test_consistency_calculation_identical_vs_variable_scores(self):
        """Verify consistency is 100% when scores are identical, and penalizes high variance."""
        act = self.activities['numbers'][0]

        # Case A: Identical scores (accuracy=80.0 across 3 sessions)
        s1 = ActivitySession(child_id=self.child_a.id, activity_id=act.id, attempts=5, correct_answers=4, accuracy=80.0, status='completed')
        s2 = ActivitySession(child_id=self.child_a.id, activity_id=act.id, attempts=5, correct_answers=4, accuracy=80.0, status='completed')
        s3 = ActivitySession(child_id=self.child_a.id, activity_id=act.id, attempts=5, correct_answers=4, accuracy=80.0, status='completed')
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        df_a = analytics_service.load_child_session_dataframe(self.child_a.id)
        consistency_a = analytics_service.compute_consistency_score(df_a)
        self.assertEqual(consistency_a, 100.0)

        # Case B: Highly variable scores for Child B (0.0% then 100.0%)
        sb1 = ActivitySession(child_id=self.child_b.id, activity_id=act.id, attempts=2, correct_answers=0, accuracy=0.0, status='completed')
        sb2 = ActivitySession(child_id=self.child_b.id, activity_id=act.id, attempts=2, correct_answers=2, accuracy=100.0, status='completed')
        db.session.add_all([sb1, sb2])
        db.session.commit()

        df_b = analytics_service.load_child_session_dataframe(self.child_b.id)
        consistency_b = analytics_service.compute_consistency_score(df_b)
        # Standard deviation between 0 and 100 is ~70.7, penalty capped at 50*2=100 -> consistency drops to 0.0
        self.assertLess(consistency_b, 50.0)

    def test_performance_score_formula_matches_weights(self):
        """Verify performance_score = accuracy*0.60 + completion*0.20 + consistency*0.20."""
        acc = 80.0
        comp = 90.0
        cons = 70.0
        # Expected: 80*0.60 (48.0) + 90*0.20 (18.0) + 70*0.20 (14.0) = 80.0
        expected = round(80.0 * 0.60 + 90.0 * 0.20 + 70.0 * 0.20, 2)
        actual = analytics_service.compute_performance_score(acc, comp, cons)
        self.assertEqual(actual, expected)
        self.assertEqual(actual, 80.0)

        # Extreme boundary test: 100% on everything
        self.assertEqual(analytics_service.compute_performance_score(100.0, 100.0, 100.0), 100.0)
        # Extreme boundary test: 0% on everything
        self.assertEqual(analytics_service.compute_performance_score(0.0, 0.0, 0.0), 0.0)

    # --- 2. Category-wise Aggregates ---

    def test_category_aggregates_breakdown(self):
        """Verify category breakdown aggregates all 5 standard categories."""
        # Add 1 visual session (100%) and 1 memory session (50%)
        s_vis = ActivitySession(
            child_id=self.child_a.id,
            activity_id=self.activities['visual'][0].id,
            attempts=3,
            correct_answers=3,
            accuracy=100.0,
            status='completed'
        )
        s_mem = ActivitySession(
            child_id=self.child_a.id,
            activity_id=self.activities['memory'][0].id,
            attempts=2,
            correct_answers=1,
            accuracy=50.0,
            status='completed'
        )
        db.session.add_all([s_vis, s_mem])
        db.session.commit()

        df = analytics_service.load_child_session_dataframe(self.child_a.id)
        aggs = analytics_service.compute_category_aggregates(df)

        # All 5 categories must be represented
        for expected_slug in ['visual', 'logic', 'numbers', 'language', 'memory']:
            self.assertIn(expected_slug, aggs)

        self.assertEqual(aggs['visual']['accuracy'], 100.0)
        self.assertEqual(aggs['visual']['sessions_count'], 1)

        self.assertEqual(aggs['memory']['accuracy'], 50.0)
        self.assertEqual(aggs['memory']['sessions_count'], 1)

        # Unplayed categories default to 0.0 accuracy and 0 sessions
        self.assertEqual(aggs['logic']['accuracy'], 0.0)
        self.assertEqual(aggs['logic']['sessions_count'], 0)

    # --- 3. Engagement Index Sensitivity ---

    def test_engagement_index_sensitivity_high_vs_low(self):
        """Verify engagement index responds with higher scores for engaged behaviors."""
        # Child A: Highly engaged (5 completed sessions across multiple categories, events logged, long duration)
        categories_to_play = ['visual', 'logic', 'numbers', 'language', 'memory']
        for idx, slug in enumerate(categories_to_play):
            act = self.activities[slug][0]
            sess = ActivitySession(
                child_id=self.child_a.id,
                activity_id=act.id,
                status='completed',
                duration_seconds=90,
                attempts=4,
                correct_answers=4,
                accuracy=100.0
            )
            db.session.add(sess)
            db.session.flush()

            # Add interaction events
            ev_start = InteractionEvent(session_id=sess.id, child_id=self.child_a.id, event_type='started')
            ev_view = InteractionEvent(session_id=sess.id, child_id=self.child_a.id, event_type='question_viewed')
            ev_ans = InteractionEvent(session_id=sess.id, child_id=self.child_a.id, event_type='answer_selected')
            ev_comp = InteractionEvent(session_id=sess.id, child_id=self.child_a.id, event_type='completed')
            db.session.add_all([ev_start, ev_view, ev_ans, ev_comp])

        # Child B: Low engagement (1 abandoned session, very short duration, only 1 category, no events)
        low_act = self.activities['visual'][0]
        sess_low = ActivitySession(
            child_id=self.child_b.id,
            activity_id=low_act.id,
            status='abandoned',
            duration_seconds=5,
            attempts=1,
            correct_answers=0,
            accuracy=0.0
        )
        db.session.add(sess_low)
        db.session.flush()
        ev_ab = InteractionEvent(session_id=sess_low.id, child_id=self.child_b.id, event_type='abandoned')
        db.session.add(ev_ab)

        db.session.commit()

        eng_high = engagement_service.compute_engagement_index(self.child_a.id)
        eng_low = engagement_service.compute_engagement_index(self.child_b.id)

        self.assertGreater(eng_high, 75.0)
        self.assertLess(eng_low, 35.0)
        self.assertGreater(eng_high, eng_low)

    # --- 4. Progress Records Population ---

    def test_progress_records_population_per_child_and_category(self):
        """Verify update_child_progress_records creates ProgressRecord rows per category."""
        # Add a session for child A in language category
        lang_act = self.activities['language'][0]
        s = ActivitySession(
            child_id=self.child_a.id,
            activity_id=lang_act.id,
            attempts=4,
            correct_answers=3,
            accuracy=75.0,
            status='completed',
            duration_seconds=80
        )
        db.session.add(s)
        db.session.commit()

        # Populate records
        records = analytics_service.update_child_progress_records(self.child_a.id)
        self.assertEqual(len(records), 5)  # 5 standard categories

        # Query database directly
        db_records = ProgressRecord.query.filter_by(child_id=self.child_a.id).all()
        self.assertEqual(len(db_records), 5)

        for rec in db_records:
            self.assertEqual(rec.child_id, self.child_a.id)
            self.assertIsNotNone(rec.category_id)
            self.assertGreaterEqual(rec.accuracy, 0.0)
            self.assertLessEqual(rec.accuracy, 100.0)
            self.assertGreaterEqual(rec.engagement_score, 0.0)
            self.assertLessEqual(rec.engagement_score, 100.0)
            self.assertGreaterEqual(rec.performance_score, 0.0)
            self.assertLessEqual(rec.performance_score, 100.0)

    # --- 5. Analytics Snapshot & API Access Control ---

    def test_analytics_snapshot_service_function(self):
        """Verify get_child_analytics_snapshot returns complete dictionary structure."""
        snapshot = analytics_service.get_child_analytics_snapshot(self.child_a.id)
        self.assertEqual(snapshot['child_id'], self.child_a.id)
        self.assertIn('overall_accuracy', snapshot)
        self.assertIn('completion_rate', snapshot)
        self.assertIn('consistency', snapshot)
        self.assertIn('performance_score', snapshot)
        self.assertIn('engagement_index', snapshot)
        self.assertIn('category_breakdown', snapshot)
        self.assertIn('total_sessions', snapshot)
        self.assertIn('weights', snapshot)

    def test_analytics_api_permissions(self):
        """Parent A and assigned teacher can view child A analytics; Parent B and unassigned teacher are blocked."""
        # 1. Parent A accesses Child A -> 200 OK
        self._login('parent_a@example.com')
        resp_a = self.client.get(f'/api/analytics/{self.child_a.id}')
        self.assertEqual(resp_a.status_code, 200)
        self.assertIn('analytics', resp_a.get_json())

        # 2. Parent B accesses Child A -> 403 Forbidden
        self._login('parent_b@example.com')
        resp_b = self.client.get(f'/api/analytics/{self.child_a.id}')
        self.assertEqual(resp_b.status_code, 403)

        # 3. Assigned Teacher 1 accesses Child A -> 200 OK
        self._login('teacher_1@example.com')
        resp_t1 = self.client.get(f'/api/analytics/{self.child_a.id}')
        self.assertEqual(resp_t1.status_code, 200)

        # 4. Unassigned Teacher 2 accesses Child A -> 403 Forbidden
        self._login('teacher_2@example.com')
        resp_t2 = self.client.get(f'/api/analytics/{self.child_a.id}')
        self.assertEqual(resp_t2.status_code, 403)

    def test_progress_api_get_and_refresh(self):
        """Parent A can query and refresh progress records via /api/progress/<child_id>."""
        self._login('parent_a@example.com')
        resp = self.client.get(f'/api/progress/{self.child_a.id}')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['child_id'], self.child_a.id)
        self.assertEqual(data['count'], 5)

        # Refresh via POST
        post_resp = self.client.post(f'/api/progress/{self.child_a.id}')
        self.assertEqual(post_resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()
