import json
import unittest
from unittest.mock import patch

from app import create_app, db
from app.models.user import User
from app.models.activity import Category, Activity
from app.agent import translation_agent, compliance_agent


class FormTranslationTestCase(unittest.TestCase):
    """
    Automated tests verifying the AI-assisted 'Translate with AI' convenience feature:
    - Translation generation and child-appropriate Hindi auto-fill
    - Human-in-the-loop: admin can edit before saving; zero auto-save
    - Compliance Agent screening of inputs and outputs
    - RBAC: non-admin roles strictly blocked from the translation endpoint
    - UI rendering of the button and feedback elements
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create admin user
        self.admin = User(name='Admin Tester', email='admin@childinsight.test', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)

        # Create parent user
        self.parent = User(name='Parent Tester', email='parent@childinsight.test', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)

        # Create teacher user
        self.teacher = User(name='Teacher Tester', email='teacher@childinsight.test', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')
        db.session.add(self.teacher)

        # Create a test category
        self.category = Category(
            name='Logic & Reasoning',
            slug='logic-reasoning',
            icon='🧩',
            description='Problem-solving, sequence recognition, and deductive puzzles.'
        )
        db.session.add(self.category)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_user(self, email, password):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Access Control (RBAC) Tests
    # -------------------------------------------------------------------------
    def test_unauthenticated_access_blocked(self):
        """Unauthenticated visitor cannot access the translate endpoint."""
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': 'Pattern Safari',
            'description': 'Find patterns'
        })
        # Should redirect to login (HTTP 302)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

    def test_parent_access_forbidden(self):
        """Parent user receives HTTP 403 Forbidden when calling translate endpoint."""
        self.login_user('parent@childinsight.test', 'ParentPass123!')
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': 'Pattern Safari',
            'description': 'Find patterns'
        })
        self.assertEqual(res.status_code, 403)

    def test_teacher_access_forbidden(self):
        """Teacher user receives HTTP 403 Forbidden when calling translate endpoint."""
        self.login_user('teacher@childinsight.test', 'TeacherPass123!')
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': 'Pattern Safari',
            'description': 'Find patterns'
        })
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 2. Compliant Suggestion Generation
    # -------------------------------------------------------------------------
    def test_admin_translate_activity_form_compliant_suggestion(self):
        """Admin receives compliant, natural Hindi translation suggestions for an activity."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': 'Pattern Safari',
            'description': 'Explore colorful patterns in the forest and spot repeating shapes.',
            'context_type': 'activity',
            'age_band': '6-9'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('title_hi', data)
        self.assertIn('description_hi', data)
        # Verify Devanagari characters are present
        has_devanagari = any('\u0900' <= char <= '\u097f' for char in data['title_hi'])
        self.assertTrue(has_devanagari, f"Expected Devanagari text in {data['title_hi']}")
        # Verify output passes compliance
        safe_t, _ = compliance_agent.check_text(data['title_hi'])
        safe_d, _ = compliance_agent.check_text(data['description_hi'])
        self.assertTrue(safe_t)
        self.assertTrue(safe_d)

    def test_admin_translate_category_form_compliant_suggestion(self):
        """Admin receives compliant Hindi translation suggestion for category form."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.post('/admin/forms/translate-ai', json={
            'name': 'Science & Nature',
            'description': 'Discover plants, animals, weather, and scientific mysteries.',
            'context_type': 'category'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('name_hi', data)
        self.assertIn('description_hi', data)
        self.assertIn('विज्ञान', data['name_hi'])

    def test_endpoint_alias_translate_ai(self):
        """The route alias /admin/translate-ai functions identically."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.post('/admin/translate-ai', json={
            'title': 'Number Grid Detective',
            'description': 'Solve playful number clues.',
            'context_type': 'activity'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

    # -------------------------------------------------------------------------
    # 3. Compliance Failure Rejection Tests
    # -------------------------------------------------------------------------
    def test_compliance_failing_english_title_rejected(self):
        """Input containing clinical/diagnostic forbidden terms is rejected before translation."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': 'ADHD Evaluation Safari',
            'description': 'Friendly patterns'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn('compliance', data['error'].lower())

    def test_compliance_failing_english_description_rejected(self):
        """Input containing deficit/disorder terminology in description is rejected."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': 'Pattern Quest',
            'description': 'Assessing learning disorder and mental deficiency in children.'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn('compliance', data['error'].lower())

    def test_compliance_failing_generated_hindi_rejected(self):
        """If the generator produces text with a forbidden Hindi clinical term, it is blocked."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        # Simulate translation result containing forbidden Hindi term 'मानसिक विकार' (mental disorder)
        bad_result = {
            'title_hi': 'मानसिक विकार पहेली',
            'name_hi': 'मानसिक विकार पहेली',
            'description_hi': 'एक सामान्य विवरण'
        }
        with patch('app.agent.translation_agent._generate_fallback_translation', return_value=bad_result):
            res = self.client.post('/admin/forms/translate-ai', json={
                'title': 'Tricky Mystery',
                'description': 'A normal puzzle'
            })
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertFalse(data['success'])
            self.assertIn('compliance', data['error'].lower())

    def test_empty_input_rejected_with_message(self):
        """Calling translation without title or description returns HTTP 400 with helpful error."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': '',
            'description': ''
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn('Please provide', data['error'])

    # -------------------------------------------------------------------------
    # 4. Human-in-the-Loop & Form Editing Verification
    # -------------------------------------------------------------------------
    def test_admin_can_edit_suggestion_and_save_form(self):
        """
        Admin gets a translation suggestion, freely edits the Hindi fields,
        and submits the form normally. The activity is saved with the edited text.
        Zero auto-save occurs before the admin explicitly submits.
        """
        self.login_user('admin@childinsight.test', 'AdminPass123!')

        # 1. Request AI translation suggestion
        res = self.client.post('/admin/forms/translate-ai', json={
            'title': 'Jungle Explorer Quest',
            'description': 'Follow animal footprints and match their sounds.',
            'context_type': 'activity'
        })
        self.assertEqual(res.status_code, 200)
        suggested_data = res.get_json()
        suggested_title_hi = suggested_data['title_hi']
        suggested_desc_hi = suggested_data['description_hi']

        # Verify activity does NOT exist yet in database (Zero auto-save guarantee)
        existing_act = Activity.query.filter_by(title='Jungle Explorer Quest').first()
        self.assertIsNone(existing_act, "Activity must not be auto-saved by translation request")

        # 2. Admin edits the suggested Hindi text before saving
        custom_edited_title_hi = suggested_title_hi + " (संशोधित संस्करण)"
        custom_edited_desc_hi = suggested_desc_hi + " शिक्षक द्वारा सत्यापित।"

        # 3. Admin submits the standard activity creation form
        form_res = self.client.post('/admin/activities/new', data={
            'title': 'Jungle Explorer Quest',
            'category_id': self.category.id,
            'difficulty': 'Easy',
            'estimated_duration': 8,
            'min_age': 6,
            'max_age': 9,
            'description': 'Follow animal footprints and match their sounds.',
            'title_hi': custom_edited_title_hi,
            'description_hi': custom_edited_desc_hi,
            'is_active': 'y'
        }, follow_redirects=True)

        self.assertEqual(form_res.status_code, 200)

        # 4. Verify saved database record contains the admin's custom edited Hindi text
        saved_act = Activity.query.filter_by(title='Jungle Explorer Quest').first()
        self.assertIsNotNone(saved_act)
        self.assertIsNotNone(saved_act.translations_json)
        trans_dict = json.loads(saved_act.translations_json)
        self.assertIn('hi', trans_dict)
        self.assertEqual(trans_dict['hi']['title'], custom_edited_title_hi)
        self.assertEqual(trans_dict['hi']['description'], custom_edited_desc_hi)

    # -------------------------------------------------------------------------
    # 5. UI Elements Presence Tests
    # -------------------------------------------------------------------------
    def test_activity_form_renders_translate_button(self):
        """The Activity Form HTML renders the 'Translate with AI' button and feedback box."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.get('/admin/activities/new')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('id="btn-translate-ai"', html)
        self.assertIn('Translate with AI', html)
        self.assertIn('id="translate-ai-feedback"', html)
        self.assertIn('title_hi', html)
        self.assertIn('description_hi', html)

    def test_category_form_renders_translate_button(self):
        """The Category Form HTML renders the 'Translate with AI' button and feedback box."""
        self.login_user('admin@childinsight.test', 'AdminPass123!')
        res = self.client.get('/admin/categories/new')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('id="btn-translate-ai"', html)
        self.assertIn('Translate with AI', html)
        self.assertIn('id="translate-ai-feedback"', html)
        self.assertIn('name_hi', html)
        self.assertIn('description_hi', html)


if __name__ == '__main__':
    unittest.main()
