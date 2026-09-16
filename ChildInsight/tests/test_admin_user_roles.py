import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.audit_log import AuditLog
from app.forms.admin import ChangeRoleForm


class AdminUserRolesTestCase(unittest.TestCase):
    """Test suite verifying admin role management, excluding child role and safeguarding role transitions."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Admin user
        self.admin = User(name='Admin User', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')

        # Target parent
        self.parent = User(name='Parent Alice', email='alice@example.com', role='parent')
        self.parent.set_password('ParentPass123!')

        # Target teacher
        self.teacher = User(name='Teacher Bob', email='bob@example.com', role='teacher')
        self.teacher.set_password('TeacherPass123!')

        db.session.add_all([self.admin, self.parent, self.teacher])
        db.session.commit()

        # Create child linked to Parent Alice
        self.child = Child(parent_id=self.parent.id, name='Charlie', age=7, grade='2nd Grade')
        db.session.add(self.child)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_model_and_form_assignable_roles(self):
        """User.ASSIGNABLE_ROLES and ChangeRoleForm must exclude 'child'."""
        self.assertEqual(User.ASSIGNABLE_ROLES, ('parent', 'teacher', 'admin'))
        self.assertNotIn('child', User.ASSIGNABLE_ROLES)

        form = ChangeRoleForm()
        role_choices = [c[0] for c in form.role.choices]
        self.assertIn('parent', role_choices)
        self.assertIn('teacher', role_choices)
        self.assertIn('admin', role_choices)
        self.assertNotIn('child', role_choices)

    def test_admin_user_management_dropdown_omits_child(self):
        """The role-change dropdown and filter dropdown on /admin/users must not include 'Child'."""
        self._login('admin@example.com', 'AdminPass123!')
        response = self.client.get('/admin/users')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')

        # Check action role-change dropdown
        self.assertIn('<option value="parent"', html)
        self.assertIn('<option value="teacher"', html)
        self.assertIn('<option value="admin"', html)
        self.assertNotIn('<option value="child"', html)
        self.assertNotIn('>Child</option>', html)

    def test_admin_role_filter_omits_child(self):
        """The role filter on /admin/users must only offer parent, teacher, admin."""
        self._login('admin@example.com', 'AdminPass123!')
        response = self.client.get('/admin/users')
        html = response.data.decode('utf-8')

        # Role filter options in the filter bar
        self.assertIn('<option value="parent"', html)
        self.assertIn('<option value="teacher"', html)
        self.assertIn('<option value="admin"', html)
        # Ensure no child option in filter select
        self.assertNotIn('<option value="child"', html)

    def test_admin_cannot_change_user_role_to_child(self):
        """Attempting to change a user's role to 'child' is rejected and role is unchanged."""
        self._login('admin@example.com', 'AdminPass123!')
        response = self.client.post(
            f'/admin/users/{self.parent.id}/change-role',
            data={'role': 'child'},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid role submitted.', response.data)

        # Confirm database role was not modified
        parent_db = db.session.get(User, self.parent.id)
        self.assertEqual(parent_db.role, 'parent')

        # Confirm no audit log was created for role change to child
        audit = AuditLog.query.filter_by(action='change_user_role', target_id=self.parent.id).first()
        self.assertIsNone(audit)

    def test_admin_can_change_valid_roles(self):
        """Admin can change user roles between parent, teacher, and admin."""
        self._login('admin@example.com', 'AdminPass123!')

        # Change parent to teacher
        response = self.client.post(
            f'/admin/users/{self.parent.id}/change-role',
            data={'role': 'teacher'},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Role for Parent Alice changed from parent to teacher.', response.data)

        parent_db = db.session.get(User, self.parent.id)
        self.assertEqual(parent_db.role, 'teacher')

        # Audit log must be recorded
        audit = AuditLog.query.filter_by(action='change_user_role', target_id=self.parent.id).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.admin.id)

        # Change teacher to parent
        response2 = self.client.post(
            f'/admin/users/{self.teacher.id}/change-role',
            data={'role': 'parent'},
            follow_redirects=True
        )
        self.assertEqual(response2.status_code, 200)
        self.assertIn(b'Role for Teacher Bob changed from teacher to parent.', response2.data)
        teacher_db = db.session.get(User, self.teacher.id)
        self.assertEqual(teacher_db.role, 'parent')

    def test_admin_cannot_demote_self(self):
        """Admin cannot change their own role away from admin."""
        self._login('admin@example.com', 'AdminPass123!')
        response = self.client.post(
            f'/admin/users/{self.admin.id}/change-role',
            data={'role': 'teacher'},
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You cannot change your own role away from admin.', response.data)

        admin_db = db.session.get(User, self.admin.id)
        self.assertEqual(admin_db.role, 'admin')


if __name__ == '__main__':
    unittest.main()
