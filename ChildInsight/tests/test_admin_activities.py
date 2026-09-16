import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.models.audit_log import AuditLog
from app.utils.seed_data import seed_activities


class AdminActivityManagementTestCase(unittest.TestCase):
    """Automated tests confirming administrative activity and question management, deactivation, and deletion protection."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create admin user
        self.admin = User(name='Admin Manager', email='admin.manage@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)

        # Create parent user
        self.parent = User(name='Parent User', email='parent.manage@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)

        # Create teacher user
        self.teacher = User(name='Teacher User', email='teacher.manage@example.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')
        db.session.add(self.teacher)

        db.session.commit()

        # Seed categories & activities
        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_user(self, email, password):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def test_non_admin_access_forbidden(self):
        """Unauthenticated and non-admin users cannot access activity management routes."""
        endpoints = [
            ('/admin/activities', 'GET'),
            ('/admin/activities/new', 'GET'),
            ('/admin/activities/new', 'POST'),
            ('/admin/activities/1/edit', 'GET'),
            ('/admin/activities/1/edit', 'POST'),
            ('/admin/activities/1/toggle-status', 'POST'),
            ('/admin/activities/1/delete', 'POST'),
            ('/admin/activities/1/questions', 'GET'),
            ('/admin/activities/1/questions/new', 'GET'),
            ('/admin/activities/1/questions/new', 'POST'),
            ('/admin/activities/1/questions/1/edit', 'GET'),
            ('/admin/activities/1/questions/1/edit', 'POST'),
            ('/admin/activities/1/questions/1/delete', 'POST'),
        ]

        # 1. Unauthenticated -> 302 redirect to login
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url, data={})
            self.assertEqual(res.status_code, 302, f"Unauthenticated request to {url} should redirect")
            self.assertIn('/auth/login', res.headers.get('Location', ''))

        # 2. Parent -> 403 Forbidden
        self.login_user('parent.manage@example.com', 'ParentPass123!')
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url, data={})
            self.assertEqual(res.status_code, 403, f"Parent request to {url} should be forbidden (403)")
        self.client.get('/auth/logout')

        # 3. Teacher -> 403 Forbidden
        self.login_user('teacher.manage@example.com', 'TeacherPass123!')
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url, data={})
            self.assertEqual(res.status_code, 403, f"Teacher request to {url} should be forbidden (403)")

    def test_activities_list_displays_activities(self):
        """Admin can view activities list with question counts, difficulty, and category."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        res = self.client.get('/admin/activities')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        self.assertIn("Educational Activities", html)
        self.assertIn("Alphabet Safari", html)
        self.assertIn("questions", html)
        self.assertIn("Active", html)

    def test_create_activity_success(self):
        """Admin creates a new activity via form; verifies DB persistence and redirect to questions."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        cat = Category.query.first()

        res = self.client.post('/admin/activities/new', data={
            'title': 'Cosmic Shapes Explorer',
            'description': 'Identify interstellar constellations and geometric shapes.',
            'category_id': cat.id,
            'difficulty': 'Medium',
            'estimated_duration': 7,
            'min_age': 6,
            'max_age': 9,
            'is_active': 'y'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Cosmic Shapes Explorer", html)
        self.assertIn("created successfully", html)

        act = Activity.query.filter_by(title='Cosmic Shapes Explorer').first()
        self.assertIsNotNone(act)
        self.assertEqual(act.difficulty, 'Medium')
        self.assertEqual(act.estimated_duration, 7)
        self.assertEqual(act.min_age, 6)
        self.assertEqual(act.max_age, 9)
        self.assertTrue(act.is_active)
        self.assertFalse(act.is_demo)

        # Audit log verification
        log = AuditLog.query.filter_by(action='create_activity', target_id=act.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user_id, self.admin.id)

    def test_edit_activity_success(self):
        """Admin can edit an activity's details."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        act = Activity.query.first()

        res = self.client.post(f'/admin/activities/{act.id}/edit', data={
            'title': f'{act.title} (Updated Edition)',
            'description': 'Updated description with new instructions.',
            'category_id': act.category_id,
            'difficulty': 'Advanced',
            'estimated_duration': 10,
            'min_age': 8,
            'max_age': 12,
            'is_active': 'y'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("updated successfully", html)

        db.session.refresh(act)
        self.assertIn("(Updated Edition)", act.title)
        self.assertEqual(act.difficulty, 'Advanced')
        self.assertEqual(act.estimated_duration, 10)
        self.assertEqual(act.min_age, 8)
        self.assertEqual(act.max_age, 12)

        # Audit log verification
        log = AuditLog.query.filter_by(action='edit_activity', target_id=act.id).first()
        self.assertIsNotNone(log)

    def test_toggle_activity_status_deactivation(self):
        """Admin can deactivate (soft-delete) and reactivate an activity."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        act = Activity.query.first()
        self.assertTrue(act.is_active)

        # Deactivate
        res = self.client.post(f'/admin/activities/{act.id}/toggle-status', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        db.session.refresh(act)
        self.assertFalse(act.is_active)
        self.assertIn("deactivated", res.data.decode('utf-8'))

        # Reactivate
        res = self.client.post(f'/admin/activities/{act.id}/toggle-status', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        db.session.refresh(act)
        self.assertTrue(act.is_active)
        self.assertIn("activated", res.data.decode('utf-8'))

    def test_hard_delete_blocked_when_sessions_exist(self):
        """Hard-deleting an activity with session history is blocked to protect data integrity."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        act = Activity.query.first()

        # Attach a session to this activity
        child = Child(name='Test Learner', age=6, grade='1st', parent_id=self.parent.id)
        db.session.add(child)
        db.session.commit()

        session_record = ActivitySession(
            child_id=child.id,
            activity_id=act.id,
            duration_seconds=120,
            attempts=5,
            correct_answers=4,
            accuracy=80.0,
            status=ActivitySession.STATUS_COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc)
        )
        db.session.add(session_record)
        db.session.commit()

        self.assertGreater(act.sessions.count(), 0)

        # Attempt delete
        res = self.client.post(f'/admin/activities/{act.id}/delete', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Cannot delete activity", html)
        self.assertIn("session record(s) attached", html)
        self.assertIn("deactivate it instead", html)

        # Confirm activity still exists in DB
        still_exists = db.session.get(Activity, act.id)
        self.assertIsNotNone(still_exists)

    def test_hard_delete_allowed_when_zero_sessions(self):
        """Hard-deleting an activity with zero sessions succeeds."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        cat = Category.query.first()

        # Create activity with 0 sessions
        new_act = Activity(
            category_id=cat.id,
            title='Temporary Exercise',
            difficulty='Easy',
            min_age=4,
            max_age=6,
            is_active=True
        )
        db.session.add(new_act)
        db.session.commit()
        act_id = new_act.id

        self.assertEqual(new_act.sessions.count(), 0)

        # Hard delete
        res = self.client.post(f'/admin/activities/{act_id}/delete', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("deleted successfully", res.data.decode('utf-8'))

        # Verify removed from DB
        deleted = db.session.get(Activity, act_id)
        self.assertIsNone(deleted)

    def test_question_crud_lifecycle(self):
        """Admin can add, edit, and delete questions for an activity."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        act = Activity.query.first()

        # 1. Add question
        res = self.client.post(f'/admin/activities/{act.id}/questions/new', data={
            'question_text': 'What color is the sky on a sunny day?',
            'question_type': 'multiple_choice',
            'options': 'Blue\nRed\nGreen\nYellow',
            'correct_answer': 'Blue',
            'hint': 'Think about sunny weather!',
            'order_num': 99
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn("added to", res.data.decode('utf-8'))

        q = ActivityQuestion.query.filter_by(question_text='What color is the sky on a sunny day?').first()
        self.assertIsNotNone(q)
        self.assertEqual(q.correct_answer, 'Blue')
        self.assertEqual(q.options, ['Blue', 'Red', 'Green', 'Yellow'])
        self.assertEqual(q.order_num, 99)

        # 2. Edit question
        res = self.client.post(f'/admin/activities/{act.id}/questions/{q.id}/edit', data={
            'question_text': 'What color is the ocean water?',
            'question_type': 'multiple_choice',
            'options': 'Deep Blue\nRuby Red\nEmerald Green',
            'correct_answer': 'Deep Blue',
            'hint': 'Waves and water!',
            'order_num': 1
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        db.session.refresh(q)
        self.assertEqual(q.question_text, 'What color is the ocean water?')
        self.assertEqual(q.correct_answer, 'Deep Blue')
        self.assertEqual(q.order_num, 1)

        # 3. Delete question
        res = self.client.post(f'/admin/activities/{act.id}/questions/{q.id}/delete', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Question removed", res.data.decode('utf-8'))

        deleted_q = db.session.get(ActivityQuestion, q.id)
        self.assertIsNone(deleted_q)

    def test_question_validation_correct_answer_must_match_options(self):
        """Question creation is rejected when the correct answer does not match any provided choice."""
        self.login_user('admin.manage@example.com', 'AdminPass123!')
        act = Activity.query.first()

        res = self.client.post(f'/admin/activities/{act.id}/questions/new', data={
            'question_text': 'Select the odd number.',
            'question_type': 'multiple_choice',
            'options': '2\n4\n6\n8',
            'correct_answer': '7',  # Not in options
            'order_num': 1
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("The correct answer &#39;7&#39; must exactly match one of the choices", html)

        # Ensure not added to DB
        q = ActivityQuestion.query.filter_by(question_text='Select the odd number.').first()
        self.assertIsNone(q)


if __name__ == '__main__':
    unittest.main()
