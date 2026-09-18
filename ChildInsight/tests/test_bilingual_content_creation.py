import json
import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.content_suggestion import ContentSuggestion
from app.agent import compliance_agent, content_integrity_agent, content_draft_agent


class BilingualContentCreationTestCase(unittest.TestCase):
    """
    Comprehensive tests ensuring consistent bilingual (English + Hindi) content creation
    is the DEFAULT across all paths in ChildInsight:
    1. Standalone AI draft generation produces both English and Hindi versions together.
    2. Manual creation with empty Hindi fields creates English-only activities that are
       flagged by Content Integrity Agent as incomplete_translation.
    3. Manual creation with Hindi fields persists translations and resolves clean in audits.
    4. Category creation with optional Hindi fields persists and renders in child hubs.
    5. Form routes enforce ethical compliance on Hindi input.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Admin user
        self.admin = User(name='Admin Test', email='admin@test.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')

        # Parent and child
        self.parent = User(name='Parent Test', email='parent@test.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')
        db.session.add_all([self.admin, self.parent])
        db.session.commit()

        self.child_en = Child(parent_id=self.parent.id, name='Aarav', age=7, preferred_language='en')
        self.child_hi = Child(parent_id=self.parent.id, name='Ananya', age=7, preferred_language='hi')
        db.session.add_all([self.child_en, self.child_hi])

        # Standard categories
        self.cat_logic = Category(name='Logic', slug='logic', icon='🧩', description='Logic and problem solving')
        self.cat_numbers = Category(name='Numbers', slug='numbers', icon='🔢', description='Math and counting')
        db.session.add_all([self.cat_logic, self.cat_numbers])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_admin(self):
        return self.client.post('/auth/login', data={
            'email': self.admin.email,
            'password': 'AdminPass123!'
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Standalone AI Draft Generation Tests
    # -------------------------------------------------------------------------
    def test_standalone_ai_draft_always_produces_both_languages(self):
        """
        Standalone AI draft generation (suggestion_id=None) must ALWAYS produce
        paired English and Hindi versions together by default.
        """
        draft = content_draft_agent.generate_draft_activity(
            category_id=self.cat_logic.id,
            age_band='6-9',
            difficulty='Easy',
            custom_guidance=None,
            suggestion_id=None
        )

        # Must have English content
        self.assertTrue(draft['title'])
        self.assertTrue(draft['description'])
        self.assertGreaterEqual(len(draft['questions']), 5)

        # Must have Hindi content by default
        self.assertTrue(draft['has_hindi'], "Standalone draft must have has_hindi=True by default.")
        self.assertIsNotNone(draft['translations'], "Standalone draft must have translations object.")
        self.assertIn('hi', draft['translations'])

        hi_data = draft['translations']['hi']
        self.assertTrue(hi_data['title'], "Hindi title must be present.")
        self.assertTrue(hi_data['description'], "Hindi description must be present.")
        self.assertGreaterEqual(len(hi_data['questions']), 5, "Hindi questions must be generated.")
        self.assertEqual(len(draft['questions']), len(hi_data['questions']), "Question counts in EN and HI must match.")

        # Check that Hindi text is strictly compliant (non-clinical)
        safe, reason = compliance_agent.check_text(hi_data['title'])
        self.assertTrue(safe, f"Hindi draft title failed compliance: {reason}")
        safe, reason = compliance_agent.check_text(hi_data['description'])
        self.assertTrue(safe, f"Hindi draft description failed compliance: {reason}")

        for hq in hi_data['questions']:
            safe_q, reason_q = compliance_agent.check_text(hq['question_text'])
            self.assertTrue(safe_q, f"Hindi question text failed compliance: {reason_q}")
            for opt in hq['options']:
                safe_opt, reason_opt = compliance_agent.check_text(opt)
                self.assertTrue(safe_opt, f"Hindi option failed compliance: {reason_opt}")
            if hq.get('hint'):
                safe_h, reason_h = compliance_agent.check_text(hq['hint'])
                self.assertTrue(safe_h, f"Hindi hint failed compliance: {reason_h}")

    # -------------------------------------------------------------------------
    # 2. Manual English-Only Activity Flagged by Content Integrity Agent
    # -------------------------------------------------------------------------
    def test_manual_english_only_activity_flagged_by_content_integrity(self):
        """
        Manual creation leaving Hindi fields blank must create English-only activity
        and Content Integrity Agent must flag it as incomplete_translation.
        """
        self.login_admin()

        # Admin posts manual activity without Hindi fields
        res = self.client.post('/admin/activities/new', data={
            'title': 'English Only Quest',
            'description': 'A fun English-only adventure challenge.',
            'title_hi': '',
            'description_hi': '',
            'category_id': self.cat_logic.id,
            'difficulty': 'Easy',
            'estimated_duration': 6,
            'min_age': 6,
            'max_age': 9,
            'is_active': 'y'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        act = Activity.query.filter_by(title='English Only Quest').first()
        self.assertIsNotNone(act)
        self.assertIsNone(act.translations_json)
        self.assertFalse(act.has_translation('hi'))

        # Add an English-only question
        res_q = self.client.post(f'/admin/activities/{act.id}/questions/new', data={
            'question_text': 'What is 1 + 1?',
            'question_type': 'multiple_choice',
            'options': '1\n2\n3\n4',
            'correct_answer': '2',
            'hint': 'Count on your fingers.',
            'question_text_hi': '',
            'options_hi': '',
            'correct_answer_hi': '',
            'hint_hi': '',
            'order_num': 1
        }, follow_redirects=True)
        self.assertEqual(res_q.status_code, 200)

        # Run integrity audit: English-only activity must be flagged as incomplete_translation (Case D)
        issues = content_integrity_agent.run_audit()
        act_issues = [i for i in issues if i.get('activity_id') == act.id and i.get('issue_type') == 'incomplete_translation']
        self.assertGreaterEqual(len(act_issues), 1, "English-only activity must be flagged as incomplete_translation.")
        self.assertIn("English-only and lacks Hindi translations", act_issues[0]['description'])

    # -------------------------------------------------------------------------
    # 3. Manual Bilingual Activity Creation & Audit Resolution
    # -------------------------------------------------------------------------
    def test_manual_bilingual_activity_persisted_and_audit_clean(self):
        """
        Manual creation with both English and Hindi fields persists translations
        properly and Content Integrity Agent does not flag incomplete_translation.
        """
        self.login_admin()

        # Admin posts bilingual activity
        res = self.client.post('/admin/activities/new', data={
            'title': 'Bilingual Logic Mystery',
            'description': 'Solve playful puzzles.',
            'title_hi': 'तर्क पहेली खोज',
            'description_hi': 'मजेदार पहेलियाँ हल करें।',
            'category_id': self.cat_logic.id,
            'difficulty': 'Medium',
            'estimated_duration': 8,
            'min_age': 6,
            'max_age': 9,
            'is_active': 'y'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        act = Activity.query.filter_by(title='Bilingual Logic Mystery').first()
        self.assertIsNotNone(act)
        self.assertTrue(act.has_translation('hi'))
        self.assertEqual(act.get_title('en'), 'Bilingual Logic Mystery')
        self.assertEqual(act.get_title('hi'), 'तर्क पहेली खोज')
        self.assertEqual(act.get_description('hi'), 'मजेदार पहेलियाँ हल करें।')

        # Add a bilingual question
        res_q = self.client.post(f'/admin/activities/{act.id}/questions/new', data={
            'question_text': 'Which clue is yellow?',
            'question_type': 'multiple_choice',
            'options': 'Banana\nApple\nGrape\nBerry',
            'correct_answer': 'Banana',
            'hint': 'It is a yellow fruit.',
            'question_text_hi': 'कौन सा फल पीला है?',
            'options_hi': 'केला\nसेब\nअंगूर\nबेरी',
            'correct_answer_hi': 'केला',
            'hint_hi': 'यह एक पीला फल है।',
            'order_num': 1
        }, follow_redirects=True)
        self.assertEqual(res_q.status_code, 200)

        q = act.questions.first()
        self.assertIsNotNone(q)
        self.assertIsNotNone(q.translations_json)
        self.assertEqual(q.get_question_text('hi'), 'कौन सा फल पीला है?')
        self.assertEqual(q.get_prompt('hi'), 'कौन सा फल पीला है?')
        self.assertEqual(q.get_correct_answer('hi'), 'केला')
        self.assertEqual(q.get_options('hi'), ['केला', 'सेब', 'अंगूर', 'बेरी'])

        # Audit should NOT flag incomplete_translation for this bilingual activity
        issues = content_integrity_agent.run_audit()
        incomplete_trans = [i for i in issues if i.get('activity_id') == act.id and i.get('issue_type') == 'incomplete_translation']
        self.assertEqual(len(incomplete_trans), 0, f"Bilingual activity should not have incomplete_translation issues: {incomplete_trans}")

    # -------------------------------------------------------------------------
    # 4. Category Bilingual Creation & Rendering
    # -------------------------------------------------------------------------
    def test_bilingual_category_creation_and_rendering(self):
        """
        Category creation with optional Hindi name and description persists in translations_json
        and renders appropriately in child activities hub for English and Hindi learners.
        """
        self.login_admin()

        res = self.client.post('/admin/categories/new', data={
            'name': 'Nature & Science',
            'description': 'Exploring flora, fauna, and ecology.',
            'icon': '🌿',
            'name_hi': 'प्रकृति और विज्ञान',
            'description_hi': 'पेड़-पौधे, जीव-जंतु और पर्यावरण की खोज।'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        cat = Category.query.filter_by(name='Nature & Science').first()
        self.assertIsNotNone(cat)
        self.assertTrue(cat.has_translation('hi'))
        self.assertEqual(cat.get_name('en'), 'Nature & Science')
        self.assertEqual(cat.get_name('hi'), 'प्रकृति और विज्ञान')
        self.assertEqual(cat.get_description('hi'), 'पेड़-पौधे, जीव-जंतु और पर्यावरण की खोज।')

        # Child view with Hindi preferred language
        res_child_hi = self.client.get(f'/child/{self.child_hi.id}/activities')
        self.assertEqual(res_child_hi.status_code, 200)
        self.assertIn('प्रकृति और विज्ञान', res_child_hi.get_data(as_text=True))

        # Child view with English preferred language
        res_child_en = self.client.get(f'/child/{self.child_en.id}/activities')
        self.assertEqual(res_child_en.status_code, 200)
        self.assertIn('Nature &amp; Science', res_child_en.get_data(as_text=True))

    # -------------------------------------------------------------------------
    # 5. Form Ethical Compliance Enforcement on Hindi Input
    # -------------------------------------------------------------------------
    def test_compliance_enforced_on_hindi_input_in_manual_forms(self):
        """
        Admin manual forms must strictly block forbidden Hindi clinical terms.
        """
        self.login_admin()

        # Category form with forbidden Hindi clinical term 'विकार'
        res_cat = self.client.post('/admin/categories/new', data={
            'name': 'Science Domain',
            'description': 'Exploring nature',
            'icon': '🔬',
            'name_hi': 'विकार अध्ययन',  # forbidden clinical term
            'description_hi': 'विवरण'
        }, follow_redirects=True)
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn('Hindi category name violates compliance', res_cat.get_data(as_text=True))
        self.assertIsNone(Category.query.filter_by(name='Science Domain').first())

        # Activity form with forbidden Hindi clinical term 'मानसिक मंदता'
        res_act = self.client.post('/admin/activities/new', data={
            'title': 'Clean Activity Title',
            'description': 'Clean description',
            'title_hi': 'मानसिक मंदता खेल',  # forbidden clinical term
            'description_hi': 'विवरण',
            'category_id': self.cat_logic.id,
            'difficulty': 'Easy',
            'estimated_duration': 5,
            'min_age': 6,
            'max_age': 9,
            'is_active': 'y'
        }, follow_redirects=True)
        self.assertEqual(res_act.status_code, 200)
        self.assertIn('Hindi activity title violates compliance', res_act.get_data(as_text=True))
        self.assertIsNone(Activity.query.filter_by(title='Clean Activity Title').first())


if __name__ == '__main__':
    unittest.main()
