"""
Automated Test Suite for Bulk Review Workflow in Orchestrator Agent (tests/test_bulk_review_workflow.py)

Validates:
1. Bulk Generate creates N unapproved drafts for N selected items.
2. Strictly ZERO activities or questions are auto-saved during bulk draft generation.
3. Content suggestions remain in STATUS_PENDING after bulk generation.
4. Individual admin approval from the bulk review screen persists only the approved draft.
5. Bulk Dismiss removes multiple items from Action Center and marks suggestions as STATUS_DISMISSED.
6. RBAC security ensures only administrators can trigger bulk generation or bulk dismissal.
"""

import json
import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.content_suggestion import ContentSuggestion
from app.agent import orchestrator_agent, compliance_agent
from app.utils.seed_data import seed_activities


class BulkReviewWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        orchestrator_agent.clear_dismissed_items()
        compliance_agent.reset_incident_history()

        # Seed users
        self.admin = User(name='Admin User', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')

        self.parent = User(name='Parent User', email='parent@example.com', role='parent')
        self.parent.set_password('ParentPass123!')

        self.child_user = User(name='Child User', email='child@example.com', role='child')
        self.child_user.set_password('ChildPass123!')

        db.session.add_all([self.admin, self.parent, self.child_user])
        db.session.commit()

        # Seed standard activities catalog
        seed_activities()

    def tearDown(self):
        orchestrator_agent.clear_dismissed_items()
        compliance_agent.reset_incident_history()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Bulk Generate: Creates N Unapproved Drafts with ZERO Auto-Saves
    # -------------------------------------------------------------------------
    def test_bulk_generate_creates_n_unapproved_drafts_zero_auto_save(self):
        """
        Confirm bulk-generate creates N unapproved drafts for N selected items
        and strictly nothing is auto-saved to Activity or ActivityQuestion tables.
        """
        self._login('admin@example.com', 'AdminPass123!')

        cat_logic = Category.query.filter_by(slug='logic').first()
        cat_numbers = Category.query.filter_by(slug='numbers').first()

        # Record initial baseline counts in database
        initial_activity_count = Activity.query.count()
        initial_question_count = ActivityQuestion.query.count()

        # Create 3 distinct pending content suggestions
        sug1 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat_logic.id,
            age_band='4-6',
            target_difficulty='Easy',
            suggested_title='Logic Adventures for Ages 4-6',
            reason='4 children aged 4-6 achieved 85% accuracy with only 1 Easy activity available.',
            priority_score=16.0,
            persistence_count=1,
            status=ContentSuggestion.STATUS_PENDING
        )
        sug2 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_TRANSLATION_GAP,
            category_id=cat_logic.id,
            age_band='9-12',
            target_difficulty='Medium',
            suggested_title='Logic Puzzles for Ages 9-12',
            reason='3 Hindi-preferring learners in age band 9-12 need translated Logic activities.',
            priority_score=24.0,
            persistence_count=2,
            status=ContentSuggestion.STATUS_PENDING
        )
        sug3 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=cat_numbers.id,
            age_band='6-9',
            target_difficulty='Beginner',
            suggested_title='Number Explorers',
            reason='8 registered learners in age band 6-9 need Beginner number foundation activities.',
            priority_score=19.0,
            persistence_count=1,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add_all([sug1, sug2, sug3])
        db.session.commit()

        # Execute Bulk Generate POST with the 3 selected suggestion IDs
        res = self.client.post('/admin/activities/ai-draft/bulk-generate', data={
            'suggestion_ids': [sug1.id, sug2.id, sug3.id]
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # 1. Verify template displays all 3 drafts together on one screen
        self.assertIn('Bulk Review AI Activity Drafts', html)
        self.assertIn('Draft #1 of 3', html)
        self.assertIn('Draft #2 of 3', html)
        self.assertIn('Draft #3 of 3', html)
        self.assertIn('3 Unsaved Drafts', html)

        # 2. STRICT READ-ONLY / ZERO AUTO-SAVE GUARANTEE:
        # Zero new activities or questions must be saved in the database
        final_activity_count = Activity.query.count()
        final_question_count = ActivityQuestion.query.count()
        self.assertEqual(final_activity_count, initial_activity_count,
                         "CRITICAL: Activity count increased during bulk draft generation! Auto-save detected.")
        self.assertEqual(final_question_count, initial_question_count,
                         "CRITICAL: Question count increased during bulk draft generation! Auto-save detected.")

        # 3. Verify all 3 suggestions remain in STATUS_PENDING
        refreshed_sug1 = db.session.get(ContentSuggestion, sug1.id)
        refreshed_sug2 = db.session.get(ContentSuggestion, sug2.id)
        refreshed_sug3 = db.session.get(ContentSuggestion, sug3.id)
        self.assertEqual(refreshed_sug1.status, ContentSuggestion.STATUS_PENDING)
        self.assertEqual(refreshed_sug2.status, ContentSuggestion.STATUS_PENDING)
        self.assertEqual(refreshed_sug3.status, ContentSuggestion.STATUS_PENDING)

    # -------------------------------------------------------------------------
    # 2. Bulk Generate from Action Center Form Post (action_center_bulk)
    # -------------------------------------------------------------------------
    def test_bulk_generate_from_action_center_bulk_endpoint(self):
        """Verify POST to /admin/action-center/bulk with bulk_action='draft' routes to bulk generation."""
        self._login('admin@example.com', 'AdminPass123!')
        cat = Category.query.filter_by(slug='language').first()

        sug = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_TRANSLATION_GAP,
            category_id=cat.id,
            age_band='6-9',
            target_difficulty='Easy',
            suggested_title='Language Fun',
            reason='2 Hindi-preferring learners need translated Language activities.',
            priority_score=18.0,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sug)
        db.session.commit()

        initial_count = Activity.query.count()

        res = self.client.post('/admin/action-center/bulk', data={
            'bulk_action': 'draft',
            'selected_keys': [f'suggestion_cat_{cat.id}']
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Bulk Review AI Activity Drafts', html)
        self.assertIn('Draft #1 of 1', html)

        # Confirm zero database mutations
        self.assertEqual(Activity.query.count(), initial_count)
        self.assertEqual(db.session.get(ContentSuggestion, sug.id).status, ContentSuggestion.STATUS_PENDING)

    # -------------------------------------------------------------------------
    # 3. Individual Human Approval from Bulk Review Screen
    # -------------------------------------------------------------------------
    def test_individual_draft_approval_from_bulk_screen(self):
        """
        Verify individual approval from the bulk review screen commits only that approved
        activity while leaving unapproved sibling drafts intact.
        """
        self._login('admin@example.com', 'AdminPass123!')
        cat = Category.query.filter_by(slug='memory').first()

        sug1 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat.id,
            age_band='6-9',
            target_difficulty='Easy',
            suggested_title='Memory Games 1',
            reason='4 children need memory expansion.',
            priority_score=15.0,
            status=ContentSuggestion.STATUS_PENDING
        )
        sug2 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat.id,
            age_band='9-12',
            target_difficulty='Medium',
            suggested_title='Memory Games 2',
            reason='5 children need memory expansion.',
            priority_score=17.0,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add_all([sug1, sug2])
        db.session.commit()

        initial_activity_count = Activity.query.count()

        # Admin approves Draft #1 via AJAX
        publish_payload = {
            'category_id': cat.id,
            'title': 'Approved Memory Discovery',
            'hi_title': 'स्मृति खोज यात्रा',
            'description': 'A wonderful memory challenge activity.',
            'hi_description': 'एक अद्भुत स्मृति गतिविधि।',
            'difficulty': 'Easy',
            'min_age': 6,
            'max_age': 9,
            'estimated_duration': 6,
            'suggestion_id': sug1.id,
            'questions_json': json.dumps([
                {
                    'question_text': 'What card was shown first?',
                    'options': ['Red Apple', 'Blue Star', 'Green Tree', 'Yellow Sun'],
                    'correct_answer': 'Red Apple',
                    'hint': 'It was a red fruit!',
                    'translations': {
                        'hi': {
                            'question_text': 'पहले कौन सा कार्ड दिखाया गया था?',
                            'options': ['लाल सेब', 'नीला तारा', 'हरा पेड़', 'पीला सूरज'],
                            'correct_answer': 'लाल सेब',
                            'hint': 'यह एक लाल फल था!'
                        }
                    }
                }
            ])
        }

        res = self.client.post(
            '/admin/activities/ai-draft/publish',
            data=publish_payload,
            headers={'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}
        )

        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data['success'])
        new_activity_id = json_data['activity_id']

        # 1. Exactly ONE activity was committed
        self.assertEqual(Activity.query.count(), initial_activity_count + 1)
        created_act = db.session.get(Activity, new_activity_id)
        self.assertEqual(created_act.title, 'Approved Memory Discovery')
        self.assertIn('स्मृति खोज यात्रा', created_act.translations_json)
        self.assertEqual(created_act.questions.count(), 1)

        # 2. Sibling suggestion sug2 remains strictly PENDING
        refreshed_sug1 = db.session.get(ContentSuggestion, sug1.id)
        refreshed_sug2 = db.session.get(ContentSuggestion, sug2.id)
        self.assertEqual(refreshed_sug1.status, ContentSuggestion.STATUS_APPROVED)
        self.assertEqual(refreshed_sug2.status, ContentSuggestion.STATUS_PENDING)

    # -------------------------------------------------------------------------
    # 4. Bulk Dismiss Workflow
    # -------------------------------------------------------------------------
    def test_bulk_dismiss_from_action_center(self):
        """
        Verify selecting multiple items and clicking 'Dismiss Selected' removes them
        from the Action Center view and marks associated suggestions as STATUS_DISMISSED.
        """
        self._login('admin@example.com', 'AdminPass123!')
        cat_logic = Category.query.filter_by(slug='logic').first()
        cat_numbers = Category.query.filter_by(slug='numbers').first()

        sug1 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_PROGRESSION_GAP,
            category_id=cat_logic.id,
            age_band='4-6',
            target_difficulty='Easy',
            suggested_title='Logic 1',
            reason='Gap in beginner logic.',
            priority_score=12.0,
            status=ContentSuggestion.STATUS_PENDING
        )
        sug2 = ContentSuggestion(
            suggestion_type=ContentSuggestion.TYPE_AGE_COVERAGE_GAP,
            category_id=cat_numbers.id,
            age_band='6-9',
            target_difficulty='Beginner',
            suggested_title='Numbers 1',
            reason='Gap in beginner numbers.',
            priority_score=14.0,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add_all([sug1, sug2])
        db.session.commit()

        # Execute Bulk Dismiss POST
        key1 = f"suggestion_cat_{cat_logic.id}"
        key2 = f"suggestion_cat_{cat_numbers.id}"

        res = self.client.post('/admin/action-center/bulk', data={
            'bulk_action': 'dismiss',
            'selected_keys': [key1, key2],
            'selected_suggestion_ids': [sug1.id, sug2.id]
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        # Verify suggestions in database are marked as STATUS_DISMISSED
        self.assertEqual(db.session.get(ContentSuggestion, sug1.id).status, ContentSuggestion.STATUS_DISMISSED)
        self.assertEqual(db.session.get(ContentSuggestion, sug2.id).status, ContentSuggestion.STATUS_DISMISSED)

        # Verify items are excluded from get_action_items
        action_items = orchestrator_agent.get_action_items()
        active_keys = {item['key'] for item in action_items}
        self.assertNotIn(key1, active_keys)
        self.assertNotIn(key2, active_keys)

    # -------------------------------------------------------------------------
    # 5. RBAC Security
    # -------------------------------------------------------------------------
    def test_bulk_review_rbac_protection(self):
        """Verify non-admin roles are forbidden from accessing bulk generate and dismiss endpoints."""
        # Unauthenticated access
        self.client.get('/logout')
        res1 = self.client.post('/admin/activities/ai-draft/bulk-generate', data={'suggestion_ids': [1]})
        self.assertEqual(res1.status_code, 302)

        res2 = self.client.post('/admin/action-center/bulk', data={'bulk_action': 'draft'})
        self.assertEqual(res2.status_code, 302)

        # Parent access blocked
        self._login('parent@example.com', 'ParentPass123!')
        res3 = self.client.post('/admin/activities/ai-draft/bulk-generate', data={'suggestion_ids': [1]}, follow_redirects=False)
        self.assertIn(res3.status_code, (302, 403))

        res4 = self.client.post('/admin/action-center/bulk', data={'bulk_action': 'dismiss'}, follow_redirects=False)
        self.assertIn(res4.status_code, (302, 403))


if __name__ == '__main__':
    unittest.main()
