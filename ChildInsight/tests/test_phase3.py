import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.utils.seed_data import seed_activities


class Phase3TestCase(unittest.TestCase):
    """Automated test suite verifying Phase 3 Activity Engine and Activity Player."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed users
        self.parent_a = User(name='Parent A', email='parent_a@example.com', role='parent')
        self.parent_a.set_password('Pass123!')

        self.parent_b = User(name='Parent B', email='parent_b@example.com', role='parent')
        self.parent_b.set_password('Pass123!')

        db.session.add_all([self.parent_a, self.parent_b])
        db.session.commit()

        # Parent A child
        self.child_a = Child(parent_id=self.parent_a.id, name='Timmy', age=6, grade='1st Grade', preferred_language='English')
        # Parent B child
        self.child_b = Child(parent_id=self.parent_b.id, name='Sara', age=7, grade='2nd Grade', preferred_language='English')

        db.session.add_all([self.child_a, self.child_b])
        db.session.commit()

        # Seed activities
        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Pass123!'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # --- 1. Seed Data Verification ---

    def test_seed_categories(self):
        """Verify 5 core learning categories exist."""
        expected_slugs = ['visual', 'logic', 'numbers', 'language', 'memory']
        for slug in expected_slugs:
            cat = Category.query.filter_by(slug=slug).first()
            self.assertIsNotNone(cat)
            self.assertIsNotNone(cat.icon)

    def test_seed_activities_and_difficulty_tiers(self):
        """Verify activities across 4 difficulty tiers."""
        self.assertGreaterEqual(Activity.query.count(), 20)
        for cat in Category.query.all():
            difficulties = [a.difficulty for a in cat.activities]
            self.assertIn('Beginner', difficulties)
            self.assertIn('Easy', difficulties)
            self.assertIn('Medium', difficulties)
            self.assertIn('Advanced', difficulties)
            for act in cat.activities:
                self.assertTrue(act.is_demo)
                self.assertGreaterEqual(act.questions.count(), 3)

    def test_question_options_and_answers(self):
        """Verify question options deserialize and match format."""
        q = ActivityQuestion.query.first()
        self.assertIsNotNone(q)
        self.assertIsInstance(q.options, list)
        self.assertGreaterEqual(len(q.options), 2)
        self.assertIn(q.correct_answer, q.options)

    # --- 2. Child Navigation & Category Hub ---

    def test_parent_views_child_activities_hub(self):
        """Parent views the category selection screen for their child."""
        self._login('parent_a@example.com')
        response = self.client.get(f'/child/{self.child_a.id}/activities')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Visual Learning', response.data)
        self.assertIn(b'Logic', response.data)
        self.assertIn(b'Numbers', response.data)

    def test_category_activity_list(self):
        """Parent views activities in a specific category."""
        self._login('parent_a@example.com')
        visual_cat = Category.query.filter_by(slug='visual').first()
        response = self.client.get(f'/child/{self.child_a.id}/category/{visual_cat.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Color Match Adventure', response.data)
        self.assertIn(b'Beginner', response.data)

    # --- 3. Activity Player Flow & Scoring ---

    def test_activity_player_scoring_flow(self):
        """Play through an activity: answer correctly and complete."""
        self._login('parent_a@example.com')
        activity = Activity.query.first()
        q1 = activity.questions.order_by(ActivityQuestion.order_num).first()

        # 1. Open question 1
        player_resp = self.client.get(f'/child/{self.child_a.id}/play/{activity.id}')
        self.assertEqual(player_resp.status_code, 200)
        self.assertIn(q1.question_text.encode(), player_resp.data)

        # 2. Submit correct answer
        ans_resp = self.client.post(
            f'/child/{self.child_a.id}/play/{activity.id}/answer',
            data={
                'question_id': q1.id,
                'selected_answer': q1.correct_answer,
                'q_idx': '0'
            }
        )
        self.assertEqual(ans_resp.status_code, 200)
        self.assertIn(b"Great job!", ans_resp.data)

        # 3. View completion results screen
        results_resp = self.client.get(f'/child/{self.child_a.id}/play/{activity.id}/results')
        self.assertEqual(results_resp.status_code, 200)
        self.assertIn(b"High Five", results_resp.data)

    def test_activity_player_incorrect_feedback(self):
        """Verify immediate encouraging feedback when answer is wrong."""
        self._login('parent_a@example.com')
        activity = Activity.query.first()
        q1 = activity.questions.order_by(ActivityQuestion.order_num).first()

        # Find wrong answer option
        wrong_choice = [opt for opt in q1.options if opt != q1.correct_answer][0]

        ans_resp = self.client.post(
            f'/child/{self.child_a.id}/play/{activity.id}/answer',
            data={
                'question_id': q1.id,
                'selected_answer': wrong_choice,
                'q_idx': '0'
            }
        )
        self.assertEqual(ans_resp.status_code, 200)
        self.assertIn(b"Good try!", ans_resp.data)
        self.assertIn(q1.correct_answer.encode(), ans_resp.data)

    # --- 4. Access Isolation & Security ---

    def test_parent_cannot_play_another_parents_child_activity(self):
        """Parent B is strictly blocked from playing activities as Parent A's child."""
        self._login('parent_b@example.com')
        activity = Activity.query.first()

        # Category hub forbidden
        hub_resp = self.client.get(f'/child/{self.child_a.id}/activities')
        self.assertEqual(hub_resp.status_code, 403)

        # Player forbidden
        play_resp = self.client.get(f'/child/{self.child_a.id}/play/{activity.id}')
        self.assertEqual(play_resp.status_code, 403)

        # Answering forbidden
        ans_resp = self.client.post(
            f'/child/{self.child_a.id}/play/{activity.id}/answer',
            data={'question_id': '1', 'selected_answer': 'any', 'q_idx': '0'}
        )
        self.assertEqual(ans_resp.status_code, 403)


if __name__ == '__main__':
    unittest.main()
