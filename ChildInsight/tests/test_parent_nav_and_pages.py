import unittest
from flask import url_for
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.teacher_assignment import TeacherAssignment
from app.models.activity import Category, Activity
from app.utils.seed_data import seed_activities


class ParentNavAndPagesTestCase(unittest.TestCase):
    """Tests Parent Dashboard navigation links, new Progress & Recommendations pages,

    child isolation (403), role enforcement (403), and elimination of placeholder links.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed test users
        self.parent_a = User(name='Parent Alice', email='alice@example.com', role='parent')
        self.parent_a.set_password('Pass123!')

        self.parent_b = User(name='Parent Bob', email='bob@example.com', role='parent')
        self.parent_b.set_password('Pass123!')

        self.teacher = User(name='Teacher Davis', email='davis@example.com', role='teacher')
        self.teacher.set_password('Pass123!')

        self.admin = User(name='Admin Charlie', email='admin@example.com', role='admin')
        self.admin.set_password('Pass123!')

        db.session.add_all([self.parent_a, self.parent_b, self.teacher, self.admin])
        db.session.commit()

        # Children
        self.child_a = Child(parent_id=self.parent_a.id, name='Leo', age=6, grade='1st Grade', preferred_language='English')
        self.child_b = Child(parent_id=self.parent_b.id, name='Maya', age=8, grade='3rd Grade', preferred_language='English')
        db.session.add_all([self.child_a, self.child_b])
        db.session.commit()

        # Teacher Assignment
        assignment = TeacherAssignment(teacher_id=self.teacher.id, child_id=self.child_a.id)
        db.session.add(assignment)
        db.session.commit()

        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Pass123!'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # -------------------------------------------------------------
    # 1. Navbar Links Verification
    # -------------------------------------------------------------
    def test_parent_navbar_renders_real_links_without_placeholders(self):
        """Verify Parent Portal navigation renders real URLs for Progress & Reports and Recommendations, with no href='#'."""
        self._login('alice@example.com')
        resp = self.client.get('/parent/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Confirm links exist with real paths
        self.assertIn('/parent/progress-reports', html)
        self.assertIn('/parent/recommendations', html)

        # Confirm no href="#" in the nav-links
        self.assertNotIn('href="#"', html)

    def test_teacher_navbar_renders_real_links_without_placeholders(self):
        """Verify Teacher Portal navigation renders real URL for Activity Assignments, with no href='#'."""
        self._login('davis@example.com')
        resp = self.client.get('/teacher/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn('/teacher/assignments', html)
        self.assertNotIn('href="#"', html)

    # -------------------------------------------------------------
    # 2. Authenticated Parent Page Access (200 OK)
    # -------------------------------------------------------------
    def test_parent_access_progress_reports_200(self):
        """Verify an authenticated parent can view Progress & Reports."""
        self._login('alice@example.com')

        # Base route
        resp = self.client.get('/parent/progress-reports')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('Progress & Learning Reports', html)
        self.assertIn('Leo', html)
        self.assertIn('Download PDF Report', html)
        self.assertIn('Download CSV Export', html)

        # Alias route
        resp_alias = self.client.get('/parent/progress')
        self.assertEqual(resp_alias.status_code, 200)

        # Explicit child_id query param
        resp_child = self.client.get(f'/parent/progress-reports?child_id={self.child_a.id}')
        self.assertEqual(resp_child.status_code, 200)
        self.assertIn('Leo', resp_child.get_data(as_text=True))

    def test_parent_access_recommendations_200(self):
        """Verify an authenticated parent can view Tailored Recommendations."""
        self._login('alice@example.com')

        resp = self.client.get('/parent/recommendations')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('Tailored Learning Recommendations', html)
        self.assertIn('Leo', html)

        # Explicit child_id query param
        resp_child = self.client.get(f'/parent/recommendations?child_id={self.child_a.id}')
        self.assertEqual(resp_child.status_code, 200)
        self.assertIn('Leo', resp_child.get_data(as_text=True))

    def test_parent_empty_state_when_no_children(self):
        """Verify proper empty state rendering when a parent has no registered children."""
        parent_empty = User(name='Parent Empty', email='empty@example.com', role='parent')
        parent_empty.set_password('Pass123!')
        db.session.add(parent_empty)
        db.session.commit()

        self._login('empty@example.com')

        resp_prog = self.client.get('/parent/progress-reports')
        self.assertEqual(resp_prog.status_code, 200)
        self.assertIn('No Registered Children Yet', resp_prog.get_data(as_text=True))

        resp_rec = self.client.get('/parent/recommendations')
        self.assertEqual(resp_rec.status_code, 200)
        self.assertIn('No Registered Children Yet', resp_rec.get_data(as_text=True))

    # -------------------------------------------------------------
    # 3. Unauthenticated Access (302 Redirect to Login)
    # -------------------------------------------------------------
    def test_unauthenticated_access_redirects(self):
        """Verify unauthenticated requests redirect to login."""
        self.client.get('/logout')

        resp1 = self.client.get('/parent/progress-reports')
        self.assertEqual(resp1.status_code, 302)
        self.assertIn('/login', resp1.headers.get('Location', ''))

        resp2 = self.client.get('/parent/recommendations')
        self.assertEqual(resp2.status_code, 302)
        self.assertIn('/login', resp2.headers.get('Location', ''))

        resp3 = self.client.get('/teacher/assignments')
        self.assertEqual(resp3.status_code, 302)
        self.assertIn('/login', resp3.headers.get('Location', ''))

    # -------------------------------------------------------------
    # 4. Role Enforcement (403 Forbidden for Non-Parents)
    # -------------------------------------------------------------
    def test_non_parent_roles_blocked_403(self):
        """Verify non-parent roles (teacher, admin) receive 403 Forbidden when accessing parent pages."""
        # Teacher
        self._login('davis@example.com')
        resp_teacher_prog = self.client.get('/parent/progress-reports')
        self.assertEqual(resp_teacher_prog.status_code, 403)

        resp_teacher_rec = self.client.get('/parent/recommendations')
        self.assertEqual(resp_teacher_rec.status_code, 403)

        # Admin
        self._login('admin@example.com')
        resp_admin_prog = self.client.get('/parent/progress-reports')
        self.assertEqual(resp_admin_prog.status_code, 403)

        resp_admin_rec = self.client.get('/parent/recommendations')
        self.assertEqual(resp_admin_rec.status_code, 403)

    # -------------------------------------------------------------
    # 5. Child Isolation (403 Forbidden on Cross-Parent Child Access)
    # -------------------------------------------------------------
    def test_parent_child_isolation_403(self):
        """Verify a parent attempting to view another parent's child receives 403 Forbidden."""
        self._login('alice@example.com')  # Parent of child_a (Leo)

        # Try to access child_b (Maya), which belongs to parent_b
        resp_prog = self.client.get(f'/parent/progress-reports?child_id={self.child_b.id}')
        self.assertEqual(resp_prog.status_code, 403)

        resp_rec = self.client.get(f'/parent/recommendations?child_id={self.child_b.id}')
        self.assertEqual(resp_rec.status_code, 403)

        # Verify parent_b also cannot access child_a
        self._login('bob@example.com')
        resp_bob_prog = self.client.get(f'/parent/progress-reports?child_id={self.child_a.id}')
        self.assertEqual(resp_bob_prog.status_code, 403)

        resp_bob_rec = self.client.get(f'/parent/recommendations?child_id={self.child_a.id}')
        self.assertEqual(resp_bob_rec.status_code, 403)

    # -------------------------------------------------------------
    # 6. Teacher Activity Assignments Access & Role Protection
    # -------------------------------------------------------------
    def test_teacher_activity_assignments_200_and_role_protection(self):
        """Verify teacher can access activity assignments, while non-teachers are blocked."""
        # Teacher access: 200 OK
        self._login('davis@example.com')
        resp = self.client.get('/teacher/assignments')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('Activity Assignments & Guided Learning', html)
        self.assertIn('Assign New Activity', html)
        self.assertIn('Leo', html)  # Assigned child

        # Parent access: 403 Forbidden
        self._login('alice@example.com')
        resp_parent = self.client.get('/teacher/assignments')
        self.assertEqual(resp_parent.status_code, 403)

    # -------------------------------------------------------------
    # 7. Child Card "Share with Teacher" Button & Navigation
    # -------------------------------------------------------------
    def test_child_card_share_button_navigation(self):
        """Confirm the 'Share with Teacher' button is on the child card and navigates directly to the share flow."""
        self._login('alice@example.com')
        resp = self.client.get('/parent/children')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        expected_href = f"/parent/children/{self.child_a.id}#share-with-teacher"
        self.assertIn(expected_href, html)
        self.assertIn('Share with Teacher</a>', html)
        self.assertIn('btn-outline btn-sm', html)
        self.assertIn('child-card-actions', html)

        # Direct navigation to child detail renders the #share-with-teacher section
        detail_resp = self.client.get(f"/parent/children/{self.child_a.id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail_html = detail_resp.get_data(as_text=True)
        self.assertIn('id="share-with-teacher"', detail_html)
        self.assertIn('Share with a Teacher', detail_html)
        self.assertIn(f"/parent/children/{self.child_a.id}/share-teacher", detail_html)


if __name__ == '__main__':
    unittest.main()
