import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.teacher_assignment import TeacherAssignment


class Phase2TestCase(unittest.TestCase):
    """Automated test suite verifying Phase 2 User Management and Access Control."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed sample accounts
        self.parent_a = User(name='Parent A', email='parent_a@example.com', role='parent')
        self.parent_a.set_password('Pass123!')

        self.parent_b = User(name='Parent B', email='parent_b@example.com', role='parent')
        self.parent_b.set_password('Pass123!')

        self.teacher_1 = User(name='Teacher One', email='teacher_1@example.com', role='teacher')
        self.teacher_1.set_password('Pass123!')

        self.teacher_2 = User(name='Teacher Two', email='teacher_2@example.com', role='teacher')
        self.teacher_2.set_password('Pass123!')

        self.admin = User(name='Admin', email='admin@example.com', role='admin')
        self.admin.set_password('Pass123!')

        db.session.add_all([self.parent_a, self.parent_b, self.teacher_1, self.teacher_2, self.admin])
        db.session.commit()

        # Parent A's child
        self.child_a = Child(parent_id=self.parent_a.id, name='Timmy', age=6, grade='1st Grade', preferred_language='English')
        db.session.add(self.child_a)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Pass123!'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # --- 1. Parent Child CRUD & Isolation ---

    def test_parent_create_child(self):
        """Parent creates a new child profile."""
        self._login('parent_a@example.com')
        response = self.client.post('/parent/children/new', data={
            'name': 'Mia',
            'age': '5',
            'grade': 'Kindergarten',
            'preferred_language': 'Spanish'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Mia', response.data)

        child = Child.query.filter_by(name='Mia').first()
        self.assertIsNotNone(child)
        self.assertEqual(child.parent_id, self.parent_a.id)

    def test_parent_can_view_and_edit_own_child(self):
        """Parent views and updates their own child."""
        self._login('parent_a@example.com')

        # View
        view_resp = self.client.get(f'/parent/children/{self.child_a.id}')
        self.assertEqual(view_resp.status_code, 200)
        self.assertIn(b'Timmy', view_resp.data)

        # Edit
        edit_resp = self.client.post(f'/parent/children/{self.child_a.id}/edit', data={
            'name': 'Timothy',
            'age': '7',
            'grade': '2nd Grade',
            'preferred_language': 'English'
        }, follow_redirects=True)

        self.assertEqual(edit_resp.status_code, 200)
        updated = db.session.get(Child, self.child_a.id)
        self.assertEqual(updated.name, 'Timothy')
        self.assertEqual(updated.age, 7)

    def test_parent_cannot_view_or_edit_another_parents_child(self):
        """Parent B is strictly forbidden from viewing or modifying Parent A's child."""
        self._login('parent_b@example.com')

        # Attempt to view Parent A's child
        view_resp = self.client.get(f'/parent/children/{self.child_a.id}')
        self.assertEqual(view_resp.status_code, 403)

        # Attempt to edit Parent A's child
        edit_resp = self.client.post(f'/parent/children/{self.child_a.id}/edit', data={
            'name': 'Hacked',
            'age': '10',
            'grade': '5th Grade',
            'preferred_language': 'English'
        })
        self.assertEqual(edit_resp.status_code, 403)

        # Child remained unchanged
        child = db.session.get(Child, self.child_a.id)
        self.assertEqual(child.name, 'Timmy')

    def test_parent_cannot_delete_another_parents_child(self):
        """Parent B cannot delete Parent A's child."""
        self._login('parent_b@example.com')
        del_resp = self.client.post(f'/parent/children/{self.child_a.id}/delete')
        self.assertEqual(del_resp.status_code, 403)
        self.assertIsNotNone(db.session.get(Child, self.child_a.id))

    def test_parent_delete_own_child(self):
        """Parent A successfully deletes own child."""
        self._login('parent_a@example.com')
        del_resp = self.client.post(f'/parent/children/{self.child_a.id}/delete', follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertIsNone(db.session.get(Child, self.child_a.id))

    # --- 2. Teacher Assignment & Scoping ---

    def test_teacher_can_view_only_assigned_child(self):
        """Teacher 1 can view assigned child; Teacher 2 is blocked."""
        # Create assignment for Teacher 1
        assignment = TeacherAssignment(teacher_id=self.teacher_1.id, child_id=self.child_a.id)
        db.session.add(assignment)
        db.session.commit()

        # Teacher 1 can view
        self._login('teacher_1@example.com')
        t1_resp = self.client.get(f'/teacher/students/{self.child_a.id}')
        self.assertEqual(t1_resp.status_code, 200)
        self.assertIn(b'Timmy', t1_resp.data)

        # Teacher 1 sees student in roster
        list_resp = self.client.get('/teacher/students')
        self.assertIn(b'Timmy', list_resp.data)

        # Teacher 2 (not assigned) is blocked
        self._login('teacher_2@example.com')
        t2_resp = self.client.get(f'/teacher/students/{self.child_a.id}')
        self.assertEqual(t2_resp.status_code, 403)

        # Teacher 2 roster is empty
        t2_list = self.client.get('/teacher/students')
        self.assertNotIn(b'Timmy', t2_list.data)

    def test_teacher_cannot_modify_or_delete_child(self):
        """Teacher cannot execute write operations on child profiles."""
        assignment = TeacherAssignment(teacher_id=self.teacher_1.id, child_id=self.child_a.id)
        db.session.add(assignment)
        db.session.commit()

        self._login('teacher_1@example.com')
        edit_resp = self.client.post(f'/parent/children/{self.child_a.id}/edit', data={'name': 'Changed'})
        self.assertEqual(edit_resp.status_code, 403)

        del_resp = self.client.post(f'/parent/children/{self.child_a.id}/delete')
        self.assertEqual(del_resp.status_code, 403)

    # --- 3. Admin User Management & Role Control ---

    def test_non_admin_cannot_access_admin_routes(self):
        """Parents and teachers receive 403 when requesting admin endpoints."""
        self._login('parent_a@example.com')
        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 403)

        self._login('teacher_1@example.com')
        resp2 = self.client.get('/admin/users')
        self.assertEqual(resp2.status_code, 403)

    def test_admin_can_toggle_user_status(self):
        """Admin can deactivate and reactivate accounts."""
        self._login('admin@example.com')

        # Deactivate Parent A
        resp = self.client.post(f'/admin/users/{self.parent_a.id}/toggle-status', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(db.session.get(User, self.parent_a.id).is_active)

        # Reactivate Parent A
        resp2 = self.client.post(f'/admin/users/{self.parent_a.id}/toggle-status', follow_redirects=True)
        self.assertEqual(resp2.status_code, 200)
        self.assertTrue(db.session.get(User, self.parent_a.id).is_active)

    def test_admin_cannot_deactivate_self(self):
        """Admin is prevented from deactivating their own account."""
        self._login('admin@example.com')
        resp = self.client.post(f'/admin/users/{self.admin.id}/toggle-status', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(db.session.get(User, self.admin.id).is_active)
        self.assertIn(b'cannot deactivate your own', resp.data)

    def test_admin_can_change_user_role(self):
        """Admin updates role of a user."""
        self._login('admin@example.com')
        resp = self.client.post(f'/admin/users/{self.parent_b.id}/change-role', data={'role': 'teacher'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(db.session.get(User, self.parent_b.id).role, 'teacher')

    def test_admin_create_and_delete_teacher_assignment(self):
        """Admin creates and deletes teacher-student assignment."""
        self._login('admin@example.com')

        # Create assignment
        assign_resp = self.client.post('/admin/assignments', data={
            'teacher_id': self.teacher_1.id,
            'child_id': self.child_a.id
        }, follow_redirects=True)
        self.assertEqual(assign_resp.status_code, 200)

        assignment = TeacherAssignment.query.filter_by(teacher_id=self.teacher_1.id, child_id=self.child_a.id).first()
        self.assertIsNotNone(assignment)

        # Delete assignment
        del_resp = self.client.post(f'/admin/assignments/{assignment.id}/delete', follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertIsNone(db.session.get(TeacherAssignment, assignment.id))


if __name__ == '__main__':
    unittest.main()
