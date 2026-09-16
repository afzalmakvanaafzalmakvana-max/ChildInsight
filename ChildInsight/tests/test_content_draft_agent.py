import json
import unittest
from app import create_app, db
from app.models.user import User
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.content_suggestion import ContentSuggestion
from app.agent import content_draft_agent
from app.utils.seed_data import seed_activities


class ContentDraftAgentTestCase(unittest.TestCase):
    """Automated tests validating AI content drafting, context grounding, safety retries, and publishing workflows."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create test users
        self.admin = User(name='Admin Content Manager', email='admin@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)

        self.teacher = User(name='Teacher Davis', email='teacher@example.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')
        db.session.add(self.teacher)

        self.parent = User(name='Parent Kelly', email='parent@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)

        db.session.commit()
        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_admin(self):
        return self.client.post('/login', data={
            'email': 'admin@example.com',
            'password': 'AdminPass123!'
        }, follow_redirects=True)

    def test_prompt_contains_real_platform_context(self):
        """Verify the agent prompt includes real existing activity titles for tone and cross-category calibration."""
        category = Category.query.filter_by(slug='visual').first()
        self.assertIsNotNone(category)

        # Get existing activities in category
        existing_acts = Activity.query.filter_by(category_id=category.id, is_active=True).all()
        self.assertTrue(len(existing_acts) > 0)
        first_act_title = existing_acts[0].title

        system_prompt, user_prompt, meta = content_draft_agent.build_generation_prompt(
            category_id=category.id,
            age_band_key='4-6',
            difficulty='Beginner'
        )

        # Confirm category name is in user prompt
        self.assertIn(category.name, user_prompt)
        self.assertIn('Ages 4-6', user_prompt)

        # Confirm real existing activity title from category is embedded
        self.assertIn(first_act_title, user_prompt)

        # Confirm cross-category calibration section is present
        self.assertIn('CROSS-CATEGORY CONTENT CALIBRATION', user_prompt)

        # Confirm PRD §4 blacklist terms are explicitly embedded in the system prompt
        self.assertIn('adhd', system_prompt)
        self.assertIn('deficit', system_prompt)
        self.assertIn('clinical', system_prompt)

    def test_prompt_contains_suggestion_reason(self):
        """Verify the agent prompt directly embeds Content Suggestion reason text to address specific gaps."""
        category = Category.query.filter_by(slug='logic').first()
        self.assertIsNotNone(category)

        suggestion = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=category.id,
            age_band='6-9',
            target_difficulty='Medium',
            suggested_title='Mirror Maze Deduction Quest',
            reason='Learners at ages 6-9 show 88% accuracy on Easy logic puzzles but lack Medium difficulty step-by-step challenges.',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(suggestion)
        db.session.commit()

        system_prompt, user_prompt, meta = content_draft_agent.build_generation_prompt(
            category_id=category.id,
            age_band_key='6-9',
            difficulty='Medium',
            suggestion_id=suggestion.id
        )

        # Confirm suggestion reason is embedded verbatim in user prompt
        self.assertIn(suggestion.reason, user_prompt)
        self.assertIn('Mirror Maze Deduction Quest', user_prompt)
        self.assertEqual(meta['suggestion_id'], suggestion.id)
        self.assertEqual(meta['addressed_gap_reason'], suggestion.reason)

    def test_compliance_question_filtering_and_retries(self):
        """Verify questions violating clinical/diagnostic blacklist trigger retries and are excluded."""
        violating_questions = [
            {
                "question_text": "Does this puzzle indicate mental deficit or abnormal delay?",
                "options": ["Yes", "No", "Maybe", "Uncertain"],
                "correct_answer": "No",
                "hint": "Assess mental deficit carefully."
            },
            {
                "question_text": "Count the golden keys hidden in the treasure cavern:",
                "options": ["3", "4", "5", "6"],
                "correct_answer": "4",
                "hint": "Count from 1 to 4 carefully."
            }
        ]

        cleaned, discarded = content_draft_agent.verify_and_clean_questions(
            violating_questions,
            category_name='Logic',
            age_band_key='6-9'
        )

        # Verify no clean question contains forbidden words
        for q in cleaned:
            self.assertNotIn('deficit', q['question_text'].lower())
            self.assertNotIn('abnormal', q['question_text'].lower())
            self.assertNotIn('adhd', q['question_text'].lower())

        # Clean question must be preserved
        clean_prompts = [q['question_text'] for q in cleaned]
        self.assertTrue(any("golden keys" in p for p in clean_prompts))

    def test_nothing_saved_until_approval(self):
        """Verify generating a draft does NOT insert anything into activities or questions tables."""
        self.login_admin()
        category = Category.query.first()

        initial_act_count = Activity.query.count()
        initial_q_count = ActivityQuestion.query.count()

        res = self.client.post('/admin/activities/ai-draft/generate', data={
            'category_id': category.id,
            'age_band': '6-9',
            'difficulty': 'Easy',
            'custom_guidance': 'Focus on hidden constellation stars'
        })
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Review screen must render with unsaved draft badge
        self.assertIn('Review AI Generated Activity Draft', html)
        self.assertIn('Unsaved Draft', html)
        self.assertIn('Platform Grounding & Context Used', html)

        # Database counts MUST be identical
        self.assertEqual(Activity.query.count(), initial_act_count)
        self.assertEqual(ActivityQuestion.query.count(), initial_q_count)

    def test_edits_before_approval_are_saved(self):
        """Verify administrator inline edits made on the review screen are what gets committed to the DB."""
        self.login_admin()
        category = Category.query.first()

        custom_title = "Polished Starship Navigation Adventure"
        custom_desc = "Guide the explorer starship through colorful cosmic rings."

        edited_questions = [
            {
                "question_text": "Which constellation forms a triangle of brilliant cyan stars?",
                "options": ["Alpha Triangle", "Beta Square", "Gamma Loop", "Delta Ring"],
                "correct_answer": "Alpha Triangle",
                "hint": "Look for 3 glowing points."
            },
            {
                "question_text": "If your speed increases from 2 to 4 to 6 light-units, what comes next?",
                "options": ["8", "7", "9", "10"],
                "correct_answer": "8",
                "hint": "Add 2 light-units each step."
            }
        ]

        res = self.client.post('/admin/activities/ai-draft/publish', data={
            'category_id': category.id,
            'title': custom_title,
            'description': custom_desc,
            'difficulty': 'Medium',
            'min_age': 9,
            'max_age': 12,
            'estimated_duration': 8,
            'questions_json': json.dumps(edited_questions)
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        # Verify activity was created with edited metadata
        created_act = Activity.query.filter_by(title=custom_title).first()
        self.assertIsNotNone(created_act)
        self.assertEqual(created_act.description, custom_desc)
        self.assertEqual(created_act.difficulty, 'Medium')
        self.assertEqual(created_act.min_age, 9)
        self.assertEqual(created_act.max_age, 12)
        self.assertEqual(created_act.is_demo, False)

        # Verify questions match administrator's edited payload
        self.assertEqual(created_act.questions.count(), 2)
        q1 = created_act.questions.filter_by(order_num=1).first()
        self.assertEqual(q1.question_text, "Which constellation forms a triangle of brilliant cyan stars?")
        self.assertEqual(q1.correct_answer, "Alpha Triangle")
        self.assertEqual(q1.hint, "Look for 3 glowing points.")

    def test_suggestion_approved_on_publish(self):
        """Verify that when a draft originates from a ContentSuggestion, publishing marks it 'approved'."""
        self.login_admin()
        category = Category.query.first()

        suggestion = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=category.id,
            age_band='4-6',
            target_difficulty='Beginner',
            suggested_title='Rainbow Pebble Sorting Quest',
            reason='Active 4-6 learners require foundational sorting practice in this domain.',
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(suggestion)
        db.session.commit()

        questions = [
            {
                "question_text": "Which pebble is the color of fresh emerald leaves?",
                "options": ["Green", "Blue", "Red", "Yellow"],
                "correct_answer": "Green",
                "hint": "Think of green grass."
            }
        ]

        res = self.client.post('/admin/activities/ai-draft/publish', data={
            'category_id': category.id,
            'title': 'Rainbow Pebble Sorting Quest',
            'description': 'Sort vibrant sparkling stones into treasure bowls.',
            'difficulty': 'Beginner',
            'min_age': 4,
            'max_age': 6,
            'estimated_duration': 5,
            'suggestion_id': suggestion.id,
            'questions_json': json.dumps(questions)
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        # Suggestion must be marked approved
        updated_sugg = db.session.get(ContentSuggestion, suggestion.id)
        self.assertEqual(updated_sugg.status, ContentSuggestion.STATUS_APPROVED)

    def test_non_admin_rbac_blocked(self):
        """Verify unauthenticated users and non-admin roles cannot access drafting or publishing."""
        # 1. Unauthenticated (redirect to login)
        res_get = self.client.get('/admin/activities/ai-draft')
        self.assertEqual(res_get.status_code, 302)

        res_post_gen = self.client.post('/admin/activities/ai-draft/generate', data={})
        self.assertEqual(res_post_gen.status_code, 302)

        res_post_pub = self.client.post('/admin/activities/ai-draft/publish', data={})
        self.assertEqual(res_post_pub.status_code, 302)

        # 2. Teacher (403 Forbidden)
        self.client.post('/login', data={'email': 'teacher@example.com', 'password': 'TeacherPass123!'})
        res_teacher = self.client.get('/admin/activities/ai-draft')
        self.assertEqual(res_teacher.status_code, 403)
        res_teacher_gen = self.client.post('/admin/activities/ai-draft/generate', data={})
        self.assertEqual(res_teacher_gen.status_code, 403)
        self.client.get('/auth/logout')

        # 3. Parent (403 Forbidden)
        self.client.post('/login', data={'email': 'parent@example.com', 'password': 'ParentPass123!'})
        res_parent = self.client.get('/admin/activities/ai-draft')
        self.assertEqual(res_parent.status_code, 403)
        res_parent_pub = self.client.post('/admin/activities/ai-draft/publish', data={})
        self.assertEqual(res_parent_pub.status_code, 403)


if __name__ == '__main__':
    unittest.main()
