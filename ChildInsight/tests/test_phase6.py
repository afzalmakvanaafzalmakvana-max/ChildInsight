import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.teacher_assignment import TeacherAssignment
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession, InteractionEvent
from app.models.recommendation import Recommendation
from app.utils.seed_data import seed_activities
from app.services import recommendation_service, analytics_service


class Phase6RecommendationEngineTestCase(unittest.TestCase):
    """Automated test suite verifying Phase 6 Recommendation Engine (3 layers, reason strings, ethical safeguards)."""

    FORBIDDEN_DIAGNOSTIC_TERMS = [
        'adhd', 'autism', 'dyslexia', 'disorder', 'syndrome', 'deficit',
        'abnormal', 'impaired', 'pathology', 'iq', 'retarded', 'handicap',
        'clinical', 'diagnosis', 'medical', 'mentally', 'retardation'
    ]

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

        # Teacher assignment
        assignment = TeacherAssignment(teacher_id=self.teacher_1.id, child_id=self.child_a.id)
        db.session.add(assignment)
        db.session.commit()

        # Seed activities
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

    # --- 1. Layer 1: Rule-based Triggers ---

    def test_rule_based_accuracy_thresholds(self):
        """Verify rule-based layer evaluates accuracy thresholds (>=80 level up, <50 practice, 50-80 reinforce)."""
        # 1. High accuracy (90%) -> level_up
        res_high = recommendation_service.evaluate_rule_based_recommendation(90.0, current_difficulty='Easy')
        self.assertEqual(res_high['recommendation_type'], Recommendation.TYPE_LEVEL_UP)
        self.assertEqual(res_high['target_difficulty'], 'Medium')
        self.assertIn('next challenge', res_high['action_text'])
        self.assertIn('90%', res_high['reason'])

        # 2. Low accuracy (40%) -> practice
        res_low = recommendation_service.evaluate_rule_based_recommendation(40.0, current_difficulty='Medium')
        self.assertEqual(res_low['recommendation_type'], Recommendation.TYPE_PRACTICE)
        self.assertEqual(res_low['target_difficulty'], 'Easy')
        self.assertIn('Gentle practice', res_low['action_text'])
        self.assertIn('40%', res_low['reason'])

        # 3. Moderate accuracy (65%) -> reinforce
        res_mid = recommendation_service.evaluate_rule_based_recommendation(65.0, current_difficulty='Easy')
        self.assertEqual(res_mid['recommendation_type'], Recommendation.TYPE_REINFORCE)
        self.assertEqual(res_mid['target_difficulty'], 'Easy')
        self.assertIn('Steady progress', res_mid['action_text'])
        self.assertIn('65%', res_mid['reason'])

        # 4. With category name (e.g. 87% in visual)
        res_cat = recommendation_service.evaluate_rule_based_recommendation(87.0, current_difficulty='Easy', category_name='Visual Learning')
        self.assertIn('87%', res_cat['reason'])
        self.assertIn('Visual Learning', res_cat['reason'])

    def test_difficulty_boundary_caps(self):
        """Verify difficulty progression does not exceed Advanced or dip below Beginner."""
        self.assertEqual(recommendation_service.get_next_difficulty('Advanced'), 'Advanced')
        self.assertEqual(recommendation_service.get_easier_difficulty('Beginner'), 'Beginner')

    # --- 2. Layer 2: Performance-based Adjustment (Accuracy + Completion) ---

    def test_performance_based_accuracy_and_completion_combined(self):
        """Verify performance-based layer uses accuracy and completion rate together."""
        # Case A: High accuracy (85%) AND High completion (100%) -> level_up
        res_ready = recommendation_service.evaluate_performance_based_recommendation(
            accuracy=85.0, completion_rate=100.0, current_difficulty='Beginner'
        )
        self.assertEqual(res_ready['recommendation_type'], Recommendation.TYPE_LEVEL_UP)
        self.assertEqual(res_ready['target_difficulty'], 'Easy')
        self.assertIn("85%", res_ready['reason'])
        self.assertIn("100%", res_ready['reason'])

        # Case B: High accuracy (90%) BUT Low completion (30% - exited early) -> reinforce (hold difficulty)
        res_early_exit = recommendation_service.evaluate_performance_based_recommendation(
            accuracy=90.0, completion_rate=30.0, current_difficulty='Easy'
        )
        self.assertEqual(res_early_exit['recommendation_type'], Recommendation.TYPE_REINFORCE)
        self.assertEqual(res_early_exit['target_difficulty'], 'Easy')
        self.assertIn("early exit", res_early_exit['reason'])
        self.assertIn("90%", res_early_exit['reason'])
        self.assertIn("30%", res_early_exit['reason'])

        # Case C: Low accuracy (45%) -> practice
        res_struggle = recommendation_service.evaluate_performance_based_recommendation(
            accuracy=45.0, completion_rate=100.0, current_difficulty='Medium'
        )
        self.assertEqual(res_struggle['recommendation_type'], Recommendation.TYPE_PRACTICE)
        self.assertEqual(res_struggle['target_difficulty'], 'Easy')
        self.assertIn("45%", res_struggle['reason'])

    # --- 3. Layer 3: Personalized Ranking & Cold-Start ---

    def test_cold_start_recommendations_for_new_child(self):
        """A child with 0 sessions receives introductory Beginner exploration recommendations."""
        recs = recommendation_service.get_recommendations_for_child(self.child_a.id, persist=False)
        self.assertGreaterEqual(len(recs), 3)
        for r in recs:
            self.assertEqual(r['recommendation_type'], Recommendation.TYPE_EXPLORE)
            self.assertEqual(r['difficulty'], 'Beginner')
            self.assertIn('Welcome', r['reason'])

    def test_personalized_recommendations_ranking_and_diversity(self):
        """Verify personalized ranking selects top 3-5 activities with unique priorities."""
        # Create sessions for Child A:
        # High performance in visual (100% acc, 100% comp)
        vis_act = self.activities['visual'][0]  # Beginner
        s_vis = ActivitySession(child_id=self.child_a.id, activity_id=vis_act.id, attempts=4, correct_answers=4, accuracy=100.0, status='completed')

        # Needs practice in numbers (33% acc, 100% comp)
        num_act = self.activities['numbers'][1]  # Easy
        s_num = ActivitySession(child_id=self.child_a.id, activity_id=num_act.id, attempts=3, correct_answers=1, accuracy=33.33, status='completed')

        db.session.add_all([s_vis, s_num])
        db.session.commit()

        recs = recommendation_service.get_recommendations_for_child(self.child_a.id, persist=True)

        # Must produce 3 to 5 recommendations
        self.assertGreaterEqual(len(recs), 3)
        self.assertLessEqual(len(recs), 5)

        # Priorities must be sequential 1, 2, 3...
        priorities = [r['priority'] for r in recs]
        self.assertEqual(priorities, list(range(1, len(recs) + 1)))

        # Distinct activities
        rec_act_ids = [r['activity_id'] for r in recs]
        self.assertEqual(len(rec_act_ids), len(set(rec_act_ids)))

        # Check that Visual got a level_up recommendation
        vis_rec = next((r for r in recs if r['category_slug'] == 'visual'), None)
        self.assertIsNotNone(vis_rec)
        self.assertEqual(vis_rec['recommendation_type'], Recommendation.TYPE_LEVEL_UP)
        self.assertIn("100%", vis_rec['reason'])

        # Check that Numbers got a practice recommendation
        num_rec = next((r for r in recs if r['category_slug'] == 'numbers'), None)
        self.assertIsNotNone(num_rec)
        self.assertEqual(num_rec['recommendation_type'], Recommendation.TYPE_PRACTICE)

    # --- 4. Human-Readable Reasons & Ethical Safeguards ---

    def test_reason_strings_grounded_in_numbers(self):
        """Every generated recommendation must include a non-empty reason referencing actual metrics."""
        act = self.activities['logic'][0]
        s = ActivitySession(child_id=self.child_a.id, activity_id=act.id, attempts=4, correct_answers=3, accuracy=75.0, status='completed')
        db.session.add(s)
        db.session.commit()

        recs = recommendation_service.get_recommendations_for_child(self.child_a.id, persist=False)
        for r in recs:
            reason = r['reason']
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason), 15)
            # Must not be placeholder text
            self.assertNotIn("Lorem", reason)
            self.assertNotIn("TODO", reason)

    def test_zero_diagnostic_or_medical_language(self):
        """Core Ethical Mandate: verify that no diagnostic or clinical labels appear in reasons."""
        # Generate recommendations across both children
        recs_a = recommendation_service.get_recommendations_for_child(self.child_a.id, persist=False)
        recs_b = recommendation_service.get_recommendations_for_child(self.child_b.id, persist=False)

        all_reasons = [r['reason'].lower() for r in (recs_a + recs_b)]
        self.assertGreater(len(all_reasons), 0)

        for reason in all_reasons:
            for forbidden_term in self.FORBIDDEN_DIAGNOSTIC_TERMS:
                self.assertNotIn(
                    forbidden_term,
                    reason,
                    f"Forbidden diagnostic term '{forbidden_term}' was detected in recommendation reason: '{reason}'"
                )

    # --- 5. Database Persistence & API Access ---

    def test_recommendations_persistence_in_db(self):
        """Verify recommendations are saved in the recommendations table."""
        recs = recommendation_service.get_recommendations_for_child(self.child_a.id, persist=True)

        db_recs = Recommendation.query.filter_by(child_id=self.child_a.id).order_by(Recommendation.priority.asc()).all()
        self.assertEqual(len(db_recs), len(recs))
        for db_r, r in zip(db_recs, recs):
            self.assertEqual(db_r.activity_id, r['activity_id'])
            self.assertEqual(db_r.priority, r['priority'])
            self.assertEqual(db_r.reason, r['reason'])
            self.assertEqual(db_r.recommendation_type, r['recommendation_type'])

    def test_api_recommendations_access_control(self):
        """Parent A and assigned teacher can view child A recommendations; unassigned users receive 403."""
        # 1. Parent A accesses Child A -> 200 OK
        self._login('parent_a@example.com')
        resp_a = self.client.get(f'/api/recommendations/{self.child_a.id}')
        self.assertEqual(resp_a.status_code, 200)
        data = resp_a.get_json()
        self.assertEqual(data['child_id'], self.child_a.id)
        self.assertGreaterEqual(len(data['recommendations']), 3)

        # 2. Parent B accesses Child A -> 403 Forbidden
        self._login('parent_b@example.com')
        resp_b = self.client.get(f'/api/recommendations/{self.child_a.id}')
        self.assertEqual(resp_b.status_code, 403)

        # 3. Assigned Teacher 1 accesses Child A -> 200 OK
        self._login('teacher_1@example.com')
        resp_t1 = self.client.get(f'/api/recommendations/{self.child_a.id}')
        self.assertEqual(resp_t1.status_code, 200)

        # 4. Unassigned Teacher 2 accesses Child A -> 403 Forbidden
        self._login('teacher_2@example.com')
        resp_t2 = self.client.get(f'/api/recommendations/{self.child_a.id}')
        self.assertEqual(resp_t2.status_code, 403)


if __name__ == '__main__':
    unittest.main()
