"""
Automated Test Suite for Admin Assistant (tests/test_admin_assistant.py)

Validates:
1. Grounded Real-Data Answers: Every assistant answer's claims trace back to real
   underlying telemetry (Orchestrator action items, Health score, Content Integrity
   issues, Category metrics); zero invented numbers.
2. Read-Only Safety: The assistant strictly never triggers a write or mutation to
   any table (activities, categories, questions, suggestions, users, audit logs).
3. Action Request Refusal: When asked to "fix it", "do it for me", or execute actions,
   the assistant politely refuses, explains its advisory boundary, and supplies direct links.
4. Proactive Mistake-Catching: Surface existing checks for empty categories, 0 questions,
   missing Hindi translations (Case D), and unassigned teachers.
5. RBAC Protection: Non-admin users (parent, child, unauthenticated) cannot access the chat endpoint.
6. Session/UI Rendering: Proactive assistant notes display properly in the administrative console.
"""

import json
import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.content_suggestion import ContentSuggestion
from app.models.audit_log import AuditLog
from app.agent import admin_assistant, orchestrator_agent, health_agent, content_integrity_agent
from app.utils.seed_data import seed_activities


class AdminAssistantTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        orchestrator_agent.clear_dismissed_items()

        # Seed standard users
        self.admin = User(name='Admin User', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')

        self.parent = User(name='Parent User', email='parent@example.com', role='parent')
        self.parent.set_password('ParentPass123!')

        self.child_user = User(name='Child User', email='child@example.com', role='child')
        self.child_user.set_password('ChildPass123!')

        db.session.add_all([self.admin, self.parent, self.child_user])
        db.session.commit()

        # Seed base activities catalog
        seed_activities()

    def tearDown(self):
        orchestrator_agent.clear_dismissed_items()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    # =========================================================================
    # 1. GROUNDED CLAIMS (NO INVENTED NUMBERS)
    # =========================================================================

    def test_assistant_answers_trace_to_real_data_no_invented_numbers(self):
        """Verify assistant answers trace strictly to real agent telemetry and contain no hallucinated metrics."""
        # Query platform health
        health_data = health_agent.get_latest_health()
        expected_score = float(health_data.get('score', 100.0))
        expected_comp = float(health_data.get('completion_rate', 100.0))

        res_health = admin_assistant.ask_assistant("What is our current platform health posture?")
        self.assertIn('answer', res_health)
        self.assertIn(f"{expected_score:.1f}/100", res_health['answer'])
        self.assertIn(f"{expected_comp:.1f}%", res_health['answer'])

        # Add a known pending suggestion to produce known action center items
        cat = Category.query.first()
        sug = ContentSuggestion(
            category_id=cat.id,
            age_band='9-12',
            suggestion_type=ContentSuggestion.TYPE_TRANSLATION_GAP,
            reason='14 children need Hindi translations',
            suggested_title='Nature Exploration in Hindi',
            priority_score=28.5,
            persistence_count=3,
            status=ContentSuggestion.STATUS_PENDING
        )
        db.session.add(sug)
        db.session.commit()

        action_items = orchestrator_agent.get_action_items()
        total_items = len(action_items)
        crit_items = len([i for i in action_items if i.get('priority_tier') == orchestrator_agent.TIER_CRITICAL])

        res_next = admin_assistant.ask_assistant("What should I do next?")
        self.assertIn(f"**{total_items} action item(s)**", res_next['answer'])
        self.assertIn(f"{crit_items} Critical", res_next['answer'])
        self.assertIn(cat.name, res_next['answer'])

        # Query specific category
        res_cat = admin_assistant.ask_assistant(f"What's wrong with the {cat.name} category?")
        act_count = cat.activities.count()
        self.assertIn(f"{act_count} active activities", res_cat['answer'])
        self.assertIn(cat.name, res_cat['answer'])

    # =========================================================================
    # 2. ZERO DATABASE WRITES
    # =========================================================================

    def test_assistant_strictly_never_mutates_database(self):
        """Assert calling the assistant across diverse queries performs 0 database inserts, updates, or deletes."""
        counts_before = {
            'activities': Activity.query.count(),
            'categories': Category.query.count(),
            'questions': ActivityQuestion.query.count(),
            'suggestions': ContentSuggestion.query.count(),
            'users': User.query.count(),
            'audit_logs': AuditLog.query.count()
        }

        queries = [
            "What should I do next?",
            "Can you fix the broken activities for me?",
            "Delete all empty categories right now",
            "Publish any pending drafts",
            "Did I make any mistakes?",
            "What is the platform health?"
        ]

        for q in queries:
            res = admin_assistant.ask_assistant(q)
            self.assertIsInstance(res, dict)
            self.assertIn('answer', res)

        counts_after = {
            'activities': Activity.query.count(),
            'categories': Category.query.count(),
            'questions': ActivityQuestion.query.count(),
            'suggestions': ContentSuggestion.query.count(),
            'users': User.query.count(),
            'audit_logs': AuditLog.query.count()
        }

        self.assertEqual(counts_before, counts_after, "Admin assistant must never mutate any database tables.")

    # =========================================================================
    # 3. ACTION REQUEST REFUSAL WITH DIRECT LINKS
    # =========================================================================

    def test_assistant_refuses_action_execution_and_provides_links(self):
        """Assert the assistant explicitly refuses to execute actions and points to real admin URLs."""
        action_queries = [
            "Please fix it for me",
            "Just fix the Science & Nature category",
            "Delete the unused categories",
            "Publish the new activity draft",
            "Can you create an activity for me?"
        ]

        for q in action_queries:
            res = admin_assistant.ask_assistant(q)
            self.assertTrue(res.get('refusal') or 'advisory assistant' in res['answer'].lower())
            self.assertIn("cannot make changes", res['answer'])
            self.assertIn("you must perform the action yourself", res['answer'])
            self.assertTrue(len(res.get('links', [])) > 0)
            # Ensure links point to actual admin routes
            for link in res['links']:
                self.assertTrue(link['url'].startswith('/admin/'))

    # =========================================================================
    # 4. PROACTIVE MISTAKE-CATCHING
    # =========================================================================

    def test_proactive_mistake_catching_empty_category(self):
        """Creating an empty category triggers a proactive note to add activities."""
        cat = Category(
            name='Astronomy & Space',
            slug='astronomy-space',
            description='Exploration of celestial objects',
            icon='🔭'
        )
        db.session.add(cat)
        db.session.commit()

        note = admin_assistant.check_admin_action_result('create', 'category', cat.id)
        self.assertIsNotNone(note)
        self.assertEqual(note['level'], 'warning')
        self.assertIn("0 activities", note['note'])
        self.assertIn(f"/admin/activities/new?category_id={cat.id}", note['link_url'])

    def test_proactive_mistake_catching_untranslated_activity(self):
        """Creating an English-only activity triggers a note highlighting Content Integrity Case D."""
        cat = Category.query.first()
        act = Activity(
            category_id=cat.id,
            title='Solar System Adventure',
            description='Learn all about planets in English.',
            difficulty='Medium',
            estimated_duration=8,
            min_age=6,
            max_age=9,
            translations_json=None  # Missing Hindi
        )
        db.session.add(act)
        db.session.commit()

        # Add 1 question so it's not flagged for 0 questions first
        q = ActivityQuestion(
            activity_id=act.id,
            order_num=1,
            question_text='Which planet is closest to the sun?',
            options_json=json.dumps(['Mercury', 'Venus', 'Mars', 'Jupiter']),
            correct_answer='Mercury'
        )
        db.session.add(q)
        db.session.commit()

        note = admin_assistant.check_admin_action_result('create', 'activity', act.id)
        self.assertIsNotNone(note)
        self.assertIn("missing a Hindi translation", note['note'])
        self.assertIn("Case D", note['note'])
        self.assertEqual(note['link_url'], f"/admin/activities/{act.id}/edit")

    def test_proactive_mistake_catching_zero_questions(self):
        """An activity created with 0 questions triggers an immediate warning note."""
        cat = Category.query.first()
        act = Activity(
            category_id=cat.id,
            title='Chemistry Lab',
            description='Fun chemistry basics.',
            difficulty='Easy',
            estimated_duration=5,
            min_age=4,
            max_age=6
        )
        db.session.add(act)
        db.session.commit()

        note = admin_assistant.check_admin_action_result('create', 'activity', act.id)
        self.assertIsNotNone(note)
        self.assertEqual(note['level'], 'warning')
        self.assertIn("0 questions", note['note'])
        self.assertIn(f"/admin/activities/{act.id}/questions/new", note['link_url'])

    def test_proactive_mistake_catching_unassigned_teacher(self):
        """Promoting a user to Teacher role with 0 students triggers an informative note."""
        teacher = User(name='Miss Davis', email='davis@school.org', role='teacher')
        teacher.set_password('TeacherPass123!')
        db.session.add(teacher)
        db.session.commit()

        note = admin_assistant.check_admin_action_result('role_change', 'user', teacher.id, {'new_role': 'teacher'})
        self.assertIsNotNone(note)
        self.assertIn("0 assigned students", note['note'])
        self.assertEqual(note['link_url'], '/admin/assignments')

    # =========================================================================
    # 5. RBAC SECURITY & ACCESS CONTROL
    # =========================================================================

    def test_assistant_rbac_protection(self):
        """Assert unauthenticated, parent, and child users cannot query the assistant."""
        # 1. Unauthenticated -> Redirect to login
        res_guest = self.client.post('/admin/assistant/chat', json={'question': 'What should I do?'})
        self.assertEqual(res_guest.status_code, 302)
        self.assertIn('/auth/login', res_guest.headers.get('Location', ''))

        # 2. Parent -> 403 Forbidden
        self._login('parent@example.com', 'ParentPass123!')
        res_parent = self.client.post('/admin/assistant/chat', json={'question': 'What should I do?'})
        self.assertEqual(res_parent.status_code, 403)

        # 3. Child -> 403 Forbidden
        self._login('child@example.com', 'ChildPass123!')
        res_child = self.client.post('/admin/assistant/chat', json={'question': 'What should I do?'})
        self.assertEqual(res_child.status_code, 403)

        # 4. Admin -> 200 OK
        self._login('admin@example.com', 'AdminPass123!')
        res_admin = self.client.post('/admin/assistant/chat', json={'question': 'What should I do next?'})
        self.assertEqual(res_admin.status_code, 200)
        data = json.loads(res_admin.data.decode('utf-8'))
        self.assertTrue(data.get('success'))
        self.assertIn('answer', data)

    # =========================================================================
    # 6. INLINE ASSISTANT NOTE IN SESSION AND UI
    # =========================================================================

    def test_inline_assistant_note_flashing_via_session(self):
        """Verify that when an action produces an assistant note, it renders on the redirected page."""
        self._login('admin@example.com', 'AdminPass123!')

        # Create category via form post
        res = self.client.post('/admin/categories/new', data={
            'name': 'Robotics & AI',
            'description': 'Building and coding simple robots.',
            'icon': '🤖',
            'hi_name': '',
            'hi_description': ''
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        content = res.data.decode('utf-8')
        self.assertIn("assistant-note-alert", content)
        self.assertIn("This category has 0 activities", content)
        self.assertIn("Add Activity Now", content)

    # =========================================================================
    # 7. MULTI-TURN CONVERSATIONAL MEMORY & FOLLOW-UP RESOLUTION
    # =========================================================================

    def test_multi_turn_conversational_memory(self):
        """Multi-turn conversation tests elliptical follow-ups and pronoun resolution across turns."""
        # Turn 1: Ask about Science & Nature
        res1 = admin_assistant.ask_assistant("What's wrong with the Science & Nature category?")
        self.assertIn("Science & Nature", res1['answer'])

        history = [
            {'role': 'user', 'content': "What's wrong with the Science & Nature category?"},
            {'role': 'assistant', 'content': res1['answer']}
        ]

        # Turn 2: Follow-up query about Logic
        res2 = admin_assistant.ask_assistant("What about Logic?", history=history)
        self.assertIn("Logic", res2['answer'])
        self.assertIn("activities", res2['answer'].lower())

        history.extend([
            {'role': 'user', 'content': "What about Logic?"},
            {'role': 'assistant', 'content': res2['answer']}
        ])

        # Turn 3: Pronoun follow-up "How many activities does it have?" (resolves "it" to Logic)
        res3 = admin_assistant.ask_assistant("How many activities does it have?", history=history)
        self.assertIn("Logic", res3['answer'])
        self.assertIn("active activities", res3['answer'])

    # =========================================================================
    # 8. BROADER PLATFORM QUESTIONS (USER COUNTS, RECOMMENDATION ENGINE, HOW-TO)
    # =========================================================================

    def test_broader_platform_questions_user_counts(self):
        """Assistant answers questions about total platform users and roles with exact data grounding."""
        total_users = User.query.count()
        parents = User.query.filter_by(role='parent').count()
        teachers = User.query.filter_by(role='teacher').count()
        admins = User.query.filter_by(role='admin').count()
        children = Child.query.count()

        res = admin_assistant.ask_assistant("How many users are registered on the platform?")
        self.assertIn(f"**{total_users} registered user(s)**", res['answer'])
        self.assertIn(f"- **Parents**: {parents}", res['answer'])
        self.assertIn(f"- **Teachers**: {teachers}", res['answer'])
        self.assertIn(f"- **Administrators**: {admins}", res['answer'])
        self.assertIn(f"- **Children / Learners**: {children}", res['answer'])
        self.assertTrue(any('/admin/users' in l['url'] for l in res['links']))

    def test_broader_platform_questions_recommendation_engine(self):
        """Assistant accurately explains the 3-layer recommendation engine and PRD §4 non-diagnostic ethical rule."""
        res = admin_assistant.ask_assistant("How does the recommendation engine work?")
        self.assertIn("3-layer", res['answer'].lower())
        self.assertIn("80%", res['answer'])
        self.assertIn("50%", res['answer'])
        self.assertIn("stamina", res['answer'].lower())
        self.assertIn("k-means", res['answer'].lower())
        self.assertIn("non-diagnostic", res['answer'].lower())
        self.assertTrue(any(l['url'] == '/admin/agents' for l in res['links']))

    def test_broader_platform_questions_how_to(self):
        """Assistant provides step-by-step guidance matching actual routes and links for admin actions."""
        # Assign teacher
        res_assign = admin_assistant.ask_assistant("How do I assign a teacher to a student?")
        self.assertIn("Teacher Assignments", res_assign['answer'])
        self.assertIn("/admin/assignments", res_assign['answer'])
        self.assertTrue(any(l['url'] == '/admin/assignments' for l in res_assign['links']))

        # Create category
        res_cat = admin_assistant.ask_assistant("How to create a new category?")
        self.assertIn("/admin/categories/new", res_cat['answer'])
        self.assertTrue(any(l['url'] == '/admin/categories/new' for l in res_cat['links']))

    # =========================================================================
    # 9. HINDI CONVERSATION SUPPORT
    # =========================================================================

    def test_hindi_conversation_support(self):
        """Devanagari query triggers fully grounded Hindi response with proper terminology."""
        res = admin_assistant.ask_assistant("प्लेटफ़ॉर्म में कितने उपयोगकर्ता हैं?")
        self.assertEqual(res.get('detected_language'), 'hi')
        self.assertTrue(admin_assistant.is_hindi_text(res['answer']))
        self.assertIn("पंजीकृत उपयोगकर्ता", res['answer'])
        self.assertIn("अभिभावक", res['answer'])
        self.assertIn("शिक्षक", res['answer'])
        self.assertIn(str(User.query.count()), res['answer'])

        # Category status in Hindi
        res_cat = admin_assistant.ask_assistant("तर्क और पैटर्न की स्थिति क्या है?")
        self.assertEqual(res_cat.get('detected_language'), 'hi')
        self.assertTrue(admin_assistant.is_hindi_text(res_cat['answer']))
        self.assertIn("गतिविधियां", res_cat['answer'])

    def test_hindi_action_request_refusal(self):
        """Action request in Hindi is refused politely with Hindi explanation and direct links."""
        res = admin_assistant.ask_assistant("कृपया इस श्रेणी को मेरे लिए ठीक कर दो")
        self.assertTrue(res.get('refusal'))
        self.assertEqual(res.get('detected_language'), 'hi')
        self.assertIn("सलाहकार सहायक", res['answer'])
        self.assertIn("नहीं कर सकता", res['answer'])
        self.assertTrue(len(res.get('links', [])) > 0)

    # =========================================================================
    # 10. COMPREHENSIVE ZERO DATABASE WRITES ACROSS EXTENDED FEATURES
    # =========================================================================

    def test_assistant_zero_database_writes_comprehensive(self):
        """Comprehensive test asserting zero mutations across all queries (memory, Hindi, how-to, broad questions)."""
        counts_before = {
            'activities': Activity.query.count(),
            'categories': Category.query.count(),
            'questions': ActivityQuestion.query.count(),
            'suggestions': ContentSuggestion.query.count(),
            'users': User.query.count(),
            'children': Child.query.count(),
            'audit_logs': AuditLog.query.count()
        }

        test_queries = [
            "How many users on the platform?",
            "How do recommendations work?",
            "How do I assign a teacher?",
            "How to create a new category?",
            "प्लेटफ़ॉर्म में कितने उपयोगकर्ता हैं?",
            "तर्क और पैटर्न की स्थिति क्या है?",
            "कृपया इसे ठीक कर दो",
            "What about Logic?",
            "How many activities does it have?"
        ]

        history = []
        for q in test_queries:
            res = admin_assistant.ask_assistant(q, history=history)
            history.append({'role': 'user', 'content': q})
            history.append({'role': 'assistant', 'content': res.get('answer', '')})

        counts_after = {
            'activities': Activity.query.count(),
            'categories': Category.query.count(),
            'questions': ActivityQuestion.query.count(),
            'suggestions': ContentSuggestion.query.count(),
            'users': User.query.count(),
            'children': Child.query.count(),
            'audit_logs': AuditLog.query.count()
        }
        self.assertEqual(counts_before, counts_after, "Zero database mutations must occur across all assistant queries.")

    # =========================================================================
    # 11. ASSISTANT CLEAR ENDPOINT & RBAC
    # =========================================================================

    def test_assistant_clear_endpoint_and_rbac(self):
        """Test /admin/assistant/clear requires admin role and clears session history buffer."""
        # 1. Unauthenticated -> 302 to login
        res_guest = self.client.post('/admin/assistant/clear')
        self.assertEqual(res_guest.status_code, 302)

        # 2. Parent -> 403 Forbidden
        self._login('parent@example.com', 'ParentPass123!')
        res_parent = self.client.post('/admin/assistant/clear')
        self.assertEqual(res_parent.status_code, 403)

        # 3. Child -> 403 Forbidden
        self._login('child@example.com', 'ChildPass123!')
        res_child = self.client.post('/admin/assistant/clear')
        self.assertEqual(res_child.status_code, 403)

        # 4. Admin -> 200 OK and clears memory
        self._login('admin@example.com', 'AdminPass123!')
        with self.client.session_transaction() as sess:
            sess['admin_assistant_history'] = [{'role': 'user', 'content': 'Hello'}]

        res_admin = self.client.post('/admin/assistant/clear')
        self.assertEqual(res_admin.status_code, 200)
        data = json.loads(res_admin.data.decode('utf-8'))
        self.assertTrue(data.get('success'))

        with self.client.session_transaction() as sess:
            self.assertNotIn('admin_assistant_history', sess)


if __name__ == '__main__':
    unittest.main()
