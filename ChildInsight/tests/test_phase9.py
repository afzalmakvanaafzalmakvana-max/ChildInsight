import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession
from app.models.recommendation import Recommendation
from app.models.teacher_assignment import TeacherAssignment
from app.models.audit_log import AuditLog
from app.services import audit_service
from app.utils.seed_data import seed_activities


class Phase9SecurityAndPolishTestCase(unittest.TestCase):
    """Test suite verifying Phase 9 Security, Polish, Audit Logging, CSRF, and Input Validation."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        seed_activities()
        self.categories = {cat.slug: cat for cat in Category.query.all()}
        self.activities = Activity.query.all()

        # Seed Users
        self.admin = User(name='Admin User', email='admin@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')

        self.teacher = User(name='Teacher Pat', email='teacher@example.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')

        self.other_teacher = User(name='Other Teacher', email='other_teacher@example.com', role='teacher', is_active=True)
        self.other_teacher.set_password('TeacherPass123!')

        self.parent = User(name='Parent Sam', email='parent@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')

        db.session.add_all([self.admin, self.teacher, self.other_teacher, self.parent])
        db.session.commit()

        # Seed Children
        self.child_1 = Child(parent_id=self.parent.id, name='Sammy Child', age=6, grade='1st Grade', preferred_language='English')
        self.child_2 = Child(parent_id=self.parent.id, name='Sally Child', age=8, grade='3rd Grade', preferred_language='English')
        db.session.add_all([self.child_1, self.child_2])
        db.session.commit()

        # Assign child_1 to teacher
        assignment = TeacherAssignment(teacher_id=self.teacher.id, child_id=self.child_1.id)
        db.session.add(assignment)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, email, password):
        self.client.get('/auth/logout', follow_redirects=True)
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    # --------------------------------------------------------------------------
    # 1. Audit Log Model & Service
    # --------------------------------------------------------------------------
    def test_audit_log_model_and_service(self):
        """Verify audit log records can be created and retrieved through audit_service."""
        entry = audit_service.log_action(
            user_id=self.admin.id,
            action='test_action',
            target_type='user',
            target_id=self.teacher.id
        )
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.action, 'test_action')
        self.assertEqual(entry.target_type, 'user')
        self.assertEqual(entry.target_id, self.teacher.id)

        recent = audit_service.get_recent_audit_logs(limit=10)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].action, 'test_action')

        filtered = audit_service.get_recent_audit_logs(action='test_action')
        self.assertEqual(len(filtered), 1)

        empty_filtered = audit_service.get_recent_audit_logs(action='non_existent')
        self.assertEqual(len(empty_filtered), 0)

    # --------------------------------------------------------------------------
    # 2. Admin Operations Audit Logging
    # --------------------------------------------------------------------------
    def test_admin_toggle_user_status_logs_audit(self):
        """Admin toggling user status generates an audit log entry."""
        self.login('admin@example.com', 'AdminPass123!')
        res = self.client.post(f'/admin/users/{self.parent.id}/toggle-status', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        logs = AuditLog.query.filter_by(action='toggle_user_status', target_id=self.parent.id).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, self.admin.id)
        self.assertEqual(logs[0].target_type, 'user')

    def test_admin_change_role_logs_audit(self):
        """Admin changing a user's role generates an audit log entry."""
        self.login('admin@example.com', 'AdminPass123!')
        res = self.client.post(f'/admin/users/{self.teacher.id}/change-role', data={
            'role': 'parent'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        logs = AuditLog.query.filter_by(action='change_user_role', target_id=self.teacher.id).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, self.admin.id)

    def test_admin_assignment_actions_log_audit(self):
        """Admin creating and deleting teacher assignments generates audit log entries."""
        self.login('admin@example.com', 'AdminPass123!')

        # Assign child_2 to teacher
        res = self.client.post('/admin/assignments', data={
            'teacher_id': self.teacher.id,
            'child_id': self.child_2.id
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        create_logs = AuditLog.query.filter_by(action='create_teacher_assignment').all()
        self.assertEqual(len(create_logs), 1)
        assignment_id = create_logs[0].target_id

        # Delete assignment
        del_res = self.client.post(f'/admin/assignments/{assignment_id}/delete', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        delete_logs = AuditLog.query.filter_by(action='delete_teacher_assignment').all()
        self.assertEqual(len(delete_logs), 1)

    def test_admin_audit_logs_viewer_access(self):
        """Audit logs page is only accessible by admin."""
        # Unauthenticated
        res = self.client.get('/admin/audit-logs', follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        # Parent forbidden
        self.login('parent@example.com', 'ParentPass123!')
        res_parent = self.client.get('/admin/audit-logs')
        self.assertEqual(res_parent.status_code, 403)

        # Admin allowed
        self.login('admin@example.com', 'AdminPass123!')
        res_admin = self.client.get('/admin/audit-logs')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'Audit Logs', res_admin.data)

    # --------------------------------------------------------------------------
    # 3. Teacher Write Actions & Logging
    # --------------------------------------------------------------------------
    def test_teacher_assign_activity_success_and_audit(self):
        """Teacher can assign an activity to an assigned student and an audit log is recorded."""
        self.login('teacher@example.com', 'TeacherPass123!')
        activity = self.activities[0]

        res = self.client.post(f'/teacher/students/{self.child_1.id}/assign-activity', data={
            'activity_id': activity.id
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify recommendation created by teacher
        rec = Recommendation.query.filter_by(
            child_id=self.child_1.id,
            activity_id=activity.id
        ).order_by(Recommendation.id.desc()).first()
        self.assertIsNotNone(rec)
        self.assertIn('Teacher Pat', rec.reason)

        # Verify audit log entry
        logs = AuditLog.query.filter_by(action='teacher_assign_activity', user_id=self.teacher.id).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].target_id, self.child_1.id)

    def test_teacher_cannot_assign_activity_to_unassigned_child(self):
        """Teacher cannot assign activity to student not in their roster (returns 403)."""
        self.login('other_teacher@example.com', 'TeacherPass123!')
        activity = self.activities[0]

        res = self.client.post(f'/teacher/students/{self.child_1.id}/assign-activity', data={
            'activity_id': activity.id
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 403)

    # --------------------------------------------------------------------------
    # 4. Search and Filtering
    # --------------------------------------------------------------------------
    def test_teacher_students_search_and_filter(self):
        """Teacher student list can search by name and filter by grade."""
        self.login('teacher@example.com', 'TeacherPass123!')

        # Search matching student
        res_match = self.client.get('/teacher/students?q=Sammy')
        self.assertEqual(res_match.status_code, 200)
        self.assertIn(b'Sammy Child', res_match.data)

        # Search non-matching student
        res_nomatch = self.client.get('/teacher/students?q=NonExistent')
        self.assertEqual(res_nomatch.status_code, 200)
        self.assertIn(b'matching students found', res_nomatch.data)

        # Filter by grade
        res_grade = self.client.get('/teacher/students?grade=1st+Grade')
        self.assertEqual(res_grade.status_code, 200)
        self.assertIn(b'Sammy Child', res_grade.data)

    def test_admin_users_search_and_filter(self):
        """Admin user list can search by query and filter by role."""
        self.login('admin@example.com', 'AdminPass123!')

        # Search by email/name
        res_search = self.client.get('/admin/users?q=Teacher')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b'Teacher Pat', res_search.data)

        # Filter by role
        res_role = self.client.get('/admin/users?role=parent')
        self.assertEqual(res_role.status_code, 200)
        self.assertIn(b'Parent Sam', res_role.data)
        self.assertNotIn(b'Teacher Pat', res_role.data)

    # --------------------------------------------------------------------------
    # 5. Input Validation
    # --------------------------------------------------------------------------
    def test_child_answer_route_validation(self):
        """Child answer submission rejects invalid question_id, empty answers, and oversized text."""
        self.login('parent@example.com', 'ParentPass123!')
        activity = self.activities[0]
        q = activity.questions[0]

        # Start session by visiting player
        self.client.get(f'/child/{self.child_1.id}/play/{activity.id}')

        # 1. Invalid question_id (not integer or <= 0)
        res_bad_qid = self.client.post(f'/child/{self.child_1.id}/play/{activity.id}/answer', data={
            'question_id': 'invalid',
            'selected_answer': 'Option A',
            'q_idx': 0
        })
        self.assertEqual(res_bad_qid.status_code, 400)

        # 2. Empty answer
        res_empty_ans = self.client.post(f'/child/{self.child_1.id}/play/{activity.id}/answer', data={
            'question_id': q.id,
            'selected_answer': '',
            'q_idx': 0
        })
        self.assertEqual(res_empty_ans.status_code, 400)

        # 3. Oversized answer (> 255 chars)
        res_huge_ans = self.client.post(f'/child/{self.child_1.id}/play/{activity.id}/answer', data={
            'question_id': q.id,
            'selected_answer': 'X' * 260,
            'q_idx': 0
        })
        self.assertEqual(res_huge_ans.status_code, 400)

        # 4. Question does not belong to activity
        other_activity = self.activities[1]
        other_q = other_activity.questions[0]
        res_mismatch_q = self.client.post(f'/child/{self.child_1.id}/play/{activity.id}/answer', data={
            'question_id': other_q.id,
            'selected_answer': 'Option A',
            'q_idx': 0
        })
        self.assertEqual(res_mismatch_q.status_code, 400)

    def test_api_session_input_validation(self):
        """API session creation strictly validates child_id and activity_id."""
        self.login('parent@example.com', 'ParentPass123!')

        # Missing payload
        res_none = self.client.post('/api/sessions', json={})
        self.assertEqual(res_none.status_code, 400)

        # Non-integer ID
        res_invalid_type = self.client.post('/api/sessions', json={
            'child_id': 'abc',
            'activity_id': 1
        })
        self.assertEqual(res_invalid_type.status_code, 400)

        # Negative ID
        res_neg = self.client.post('/api/sessions', json={
            'child_id': -5,
            'activity_id': 1
        })
        self.assertEqual(res_neg.status_code, 400)

    # --------------------------------------------------------------------------
    # 6. CSRF Protection Enforcement
    # --------------------------------------------------------------------------
    def test_csrf_protection_rejects_missing_token_when_enabled(self):
        """When CSRF is enabled, POST requests without a valid CSRF token return 400."""
        # Create an app instance with WTF_CSRF_ENABLED = True
        csrf_app = create_app('testing')
        csrf_app.config['WTF_CSRF_ENABLED'] = True
        csrf_client = csrf_app.test_client()

        with csrf_app.app_context():
            # Attempt login POST without CSRF token
            res = csrf_client.post('/auth/login', data={
                'email': 'admin@example.com',
                'password': 'AdminPass123!'
            })
            # Flask-WTF responds with 400 Bad Request on missing CSRF token
            self.assertEqual(res.status_code, 400)
            self.assertIn(b'Bad Request', res.data)

    # --------------------------------------------------------------------------
    # 7. Friendly Custom Error Pages
    # --------------------------------------------------------------------------
    def test_friendly_error_pages_render(self):
        """Custom error templates render with proper status codes and messages."""
        # 404
        res_404 = self.client.get('/this-route-does-not-exist-anywhere')
        self.assertEqual(res_404.status_code, 404)
        self.assertIn(b'Page Not Found', res_404.data)

        # 403
        self.login('parent@example.com', 'ParentPass123!')
        res_403 = self.client.get('/admin/dashboard')
        self.assertEqual(res_403.status_code, 403)
        self.assertIn(b'Access Forbidden', res_403.data)

        # 500 must strictly contain "Something went wrong. Please try again." per rules.md
        with self.app.test_request_context():
            from flask import render_template
            html = render_template('errors/500.html')
            self.assertIn('Something went wrong. Please try again.', html)


if __name__ == '__main__':
    unittest.main()
