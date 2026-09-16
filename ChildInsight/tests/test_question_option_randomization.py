import unittest
import re
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.utils.seed_data import seed_activities


class QuestionOptionRandomizationTestCase(unittest.TestCase):
    """Verifies that question answer options are dynamically randomized on render in the

    activity player so the correct answer does NOT always appear as the first choice,
    while scoring strictly evaluates against the correct answer regardless of display position.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed full activity dataset across all 5 categories
        seed_activities()

        # Create test parent and child
        self.parent = User(name='Parent Alice', email='alice@example.com', role='parent')
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)
        db.session.commit()

        self.child = Child(
            parent_id=self.parent.id,
            name='Leo',
            age=6,
            grade='1st Grade',
            preferred_language='English'
        )
        db.session.add(self.child)
        db.session.commit()

        # Log in parent
        self.client.post('/auth/login', data={
            'email': 'alice@example.com',
            'password': 'ParentPass123!'
        })

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _get_rendered_option_buttons(self, html):
        """Extracts option button values in exact rendered HTML order."""
        return re.findall(
            r'<button[^>]*name="selected_answer"[^>]*value="([^"]+)"',
            html,
            re.IGNORECASE
        )

    def test_seed_data_stores_correct_answer_first_by_convention(self):
        """Demonstrates the baseline condition: in stored seed data (options_json),

        the correct answer is authored as the first option.
        This proves why render-time randomization is necessary to prevent position guessing.
        """
        questions = ActivityQuestion.query.all()
        self.assertGreater(len(questions), 50, "Expected full seeded question dataset")

        first_pos_count = sum(1 for q in questions if q.options and q.options[0] == q.correct_answer)
        # In seed data, the vast majority of questions were authored with correct answer at index 0
        ratio = first_pos_count / len(questions)
        self.assertGreater(ratio, 0.70, f"Expected >70% of seed questions to have answer at index 0 in DB, got {ratio:.2%}")

    def test_render_randomizes_option_order_across_multiple_views(self):
        """Rendering the same question 20 times must produce multiple distinct visual

        positions for the correct answer, confirming it is NOT always first.
        """
        activity = Activity.query.filter(Activity.questions.any()).first()
        self.assertIsNotNone(activity)
        q = activity.questions.order_by(ActivityQuestion.order_num).first()
        self.assertGreaterEqual(len(q.options), 3)

        stored_options_before = list(q.options)
        stored_json_before = q.options_json

        positions = []
        for _ in range(20):
            res = self.client.get(f'/child/{self.child.id}/play/{activity.id}?q=0')
            self.assertEqual(res.status_code, 200)

            html = res.data.decode('utf-8')
            rendered_opts = self._get_rendered_option_buttons(html)

            # Assert complete set preservation
            self.assertEqual(len(rendered_opts), len(q.options))
            self.assertEqual(set(rendered_opts), set(q.options))

            # Record position of correct answer
            correct_idx = rendered_opts.index(q.correct_answer)
            positions.append(correct_idx)

        # Confirm correct answer is NOT always at index 0
        unique_positions = set(positions)
        self.assertGreater(
            len(unique_positions), 1,
            f"Expected correct answer to appear in multiple distinct visual positions across 20 renders, got: {positions}"
        )

        # Confirm underlying database records remain unmutated
        db.session.refresh(q)
        self.assertEqual(q.options, stored_options_before, "Database options array must remain unmutated")
        self.assertEqual(q.options_json, stored_json_before, "Database options_json string must remain unmutated")

    def test_randomization_across_all_five_categories(self):
        """Verify dynamic option randomization works reliably across all 5 cognitive domains:

        Visual Learning, Logic, Numbers, Language, and Memory.
        """
        categories = Category.query.all()
        self.assertEqual(len(categories), 5, "Expected 5 distinct categories")

        for cat in categories:
            activity = Activity.query.filter_by(category_id=cat.id).filter(Activity.questions.any()).first()
            self.assertIsNotNone(activity, f"Expected activity with questions in category {cat.name}")

            q = activity.questions.order_by(ActivityQuestion.order_num).first()
            self.assertGreaterEqual(len(q.options), 3)

            positions = []
            for _ in range(12):
                res = self.client.get(f'/child/{self.child.id}/play/{activity.id}?q=0')
                self.assertEqual(res.status_code, 200)
                html = res.data.decode('utf-8')
                rendered_opts = self._get_rendered_option_buttons(html)
                positions.append(rendered_opts.index(q.correct_answer))

            unique_pos = set(positions)
            self.assertGreater(
                len(unique_pos), 1,
                f"Category '{cat.name}' question correct answer must appear in multiple positions, got {positions}"
            )

    def test_scoring_matches_correct_answer_regardless_of_display_position(self):
        """Submitting the correct answer must award points and show positive feedback

        regardless of which button position it occupied.
        """
        activity = Activity.query.filter(Activity.questions.any()).first()
        q = activity.questions.order_by(ActivityQuestion.order_num).first()

        # Submit correct answer directly
        res = self.client.post(
            f'/child/{self.child.id}/play/{activity.id}/answer',
            data={
                'question_id': q.id,
                'selected_answer': q.correct_answer,
                'q_idx': 0
            }
        )
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertTrue("Great job!" in html and ("That's right!" in html or "That&#39;s right!" in html))

    def test_scoring_rejects_distractor_answers(self):
        """Submitting an incorrect distractor answer must not award points and show gentle feedback."""
        activity = Activity.query.filter(Activity.questions.any()).first()
        q = activity.questions.order_by(ActivityQuestion.order_num).first()

        wrong_options = [opt for opt in q.options if opt.strip().lower() != q.correct_answer.strip().lower()]
        self.assertTrue(len(wrong_options) > 0)
        wrong_choice = wrong_options[0]

        res = self.client.post(
            f'/child/{self.child.id}/play/{activity.id}/answer',
            data={
                'question_id': q.id,
                'selected_answer': wrong_choice,
                'q_idx': 0
            }
        )
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Good try! The answer was", html)
        self.assertNotIn("Great job! That's right!", html)

    def test_model_shuffled_options_property_behavior(self):
        """The ActivityQuestion.shuffled_options property must return a shuffled copy

        without mutating the underlying question.options list.
        """
        q = ActivityQuestion.query.filter(ActivityQuestion.options_json.isnot(None)).first()
        self.assertIsNotNone(q)
        self.assertGreaterEqual(len(q.options), 3)

        original_options = list(q.options)
        shuffled_samples = [tuple(q.shuffled_options) for _ in range(25)]

        # Must produce multiple distinct permutations
        unique_permutations = set(shuffled_samples)
        self.assertGreater(len(unique_permutations), 1, "shuffled_options must produce varied orderings")

        # Original options property remains unmodified
        self.assertEqual(q.options, original_options, "q.options must remain in original stored order")


if __name__ == '__main__':
    unittest.main()
