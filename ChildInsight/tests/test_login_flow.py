import unittest
import re
from app import create_app, db
from app.models.user import User
from app.models.child import Child


class LoginFlowTestCase(unittest.TestCase):
    """
    Automated test suite verifying login behavior:
    1. Next redirect preservation and correct redirect upon successful login.
    2. Role-incompatible and auth-loop 'next' parameters safely fallback to role dashboards.
    3. Stale, expired, or missing CSRF tokens show user-visible error messages.
    4. Any failed login attempt (wrong credentials, invalid format, missing fields, deactivated account)
       always displays a clear, user-visible error message.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create active test users across roles
        self.parent = User(name='Parent Alice', email='parent@example.com', role='parent')
        self.parent.set_password('ParentPass123!')

        self.teacher = User(name='Teacher Bob', email='teacher@example.com', role='teacher')
        self.teacher.set_password('TeacherPass123!')

        self.admin = User(name='Admin Charlie', email='admin@childinsight.local', role='admin')
        self.admin.set_password('AdminPass123!')

        self.child_user = User(name='Child Dan', email='child@example.com', role='child')
        self.child_user.set_password('ChildPass123!')

        # Deactivated user
        self.inactive_user = User(name='Inactive User', email='inactive@example.com', role='parent', is_active=False)
        self.inactive_user.set_password('InactivePass123!')

        db.session.add_all([self.parent, self.teacher, self.admin, self.child_user, self.inactive_user])
        db.session.commit()

        # Link child profile
        self.child = Child(
            id=self.child_user.id,
            parent_id=self.parent.id,
            name='Dan',
            age=7,
            grade='2nd Grade',
            preferred_language='English'
        )
        db.session.add(self.child)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # --- 1. Next Parameter Tests ---

    def test_login_page_renders_and_preserves_next_param(self):
        """GET /auth/login?next=/parent/progress-reports preserves next in form action and hidden input."""
        res = self.client.get('/auth/login?next=/parent/progress-reports')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('next=/parent/progress-reports', html)
        self.assertIn('name="next"', html)
        self.assertIn('value="/parent/progress-reports"', html)

    def test_login_with_next_query_param_redirects_correctly(self):
        """Valid login with ?next=/parent/progress-reports redirects directly to the target."""
        res = self.client.post('/auth/login?next=/parent/progress-reports', data={
            'email': 'parent@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/parent/progress-reports')

    def test_login_with_next_form_body_redirects_correctly(self):
        """Valid login with next supplied in form data redirects directly to the target."""
        res = self.client.post('/login', data={
            'email': 'child@example.com',
            'password': 'ChildPass123!',
            'next': '/child/home'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/child/home')

    def test_login_with_role_incompatible_next_falls_back_safely(self):
        """Parent attempting to login with next=/admin/dashboard safely falls back to parent dashboard."""
        res = self.client.post('/auth/login?next=/admin/dashboard', data={
            'email': 'parent@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/parent/dashboard')

        # Teacher attempting to login with next=/admin/users safely falls back to teacher dashboard
        res_teacher = self.client.post('/auth/login?next=/admin/users', data={
            'email': 'teacher@example.com',
            'password': 'TeacherPass123!'
        }, follow_redirects=False)

        self.assertEqual(res_teacher.status_code, 302)
        self.assertEqual(res_teacher.headers.get('Location'), '/teacher/dashboard')

    def test_login_with_looping_next_falls_back_safely(self):
        """Logging in with next=/login or next=/auth/login redirects to role dashboard, avoiding redirect loops."""
        for loop_target in ['/login', '/auth/login', '/auth/login/']:
            res = self.client.post(f'/auth/login?next={loop_target}', data={
                'email': 'parent@example.com',
                'password': 'ParentPass123!'
            }, follow_redirects=False)

            self.assertEqual(res.status_code, 302)
            self.assertEqual(res.headers.get('Location'), '/parent/dashboard')

    def test_login_with_logout_next_falls_back_safely(self):
        """Logging in with next=/logout or next=/auth/logout redirects to role dashboard, avoiding instant logout."""
        res = self.client.post('/auth/login?next=/logout', data={
            'email': 'parent@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/parent/dashboard')

    def test_login_with_external_host_next_rejected(self):
        """Targeting an external domain falls back to the user's role dashboard."""
        res = self.client.post('/auth/login?next=https://malicious-site.example.com/steal', data={
            'email': 'parent@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/parent/dashboard')

    def test_login_with_local_domain_email_succeeds(self):
        """Admin with .local domain (admin@childinsight.local) logs in successfully."""
        res = self.client.post('/login', data={
            'email': 'admin@childinsight.local',
            'password': 'AdminPass123!'
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/admin/dashboard')

    # --- 2. CSRF Token Tests ---

    def test_login_with_tampered_csrf_token_displays_clear_error(self):
        """When CSRF is enabled, posting a tampered token shows a clear user-visible error message."""
        csrf_app = create_app('development')
        with csrf_app.test_client() as csrf_client:
            res_get = csrf_client.get('/login')
            match = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', res_get.data.decode('utf-8'))
            self.assertIsNotNone(match)

            res = csrf_client.post('/login', data={
                'email': 'parent@example.com',
                'password': 'ParentPass123!',
                'csrf_token': match.group(1) + '_tampered_invalid'
            })

            html = res.data.decode('utf-8')
            # Status should be 400 with user-visible error message
            self.assertEqual(res.status_code, 400)
            self.assertTrue(
                ('session or security token has expired' in html.lower()) or
                ('csrf token is invalid' in html.lower())
            )

    def test_login_with_missing_csrf_token_displays_clear_error(self):
        """When CSRF is enabled, posting without a token shows a clear user-visible error message."""
        csrf_app = create_app('development')
        with csrf_app.test_client() as csrf_client:
            res = csrf_client.post('/login', data={
                'email': 'parent@example.com',
                'password': 'ParentPass123!'
            })

            html = res.data.decode('utf-8')
            self.assertEqual(res.status_code, 400)
            self.assertTrue(
                ('session or security token has expired' in html.lower()) or
                ('csrf token is missing' in html.lower())
            )

    # --- 3. Failed Login Error Message Tests ---

    def test_login_failure_wrong_password_shows_visible_error(self):
        """Login failure with wrong password displays user-visible error banner."""
        res = self.client.post('/login', data={
            'email': 'parent@example.com',
            'password': 'WrongPassword123'
        })
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Invalid email address or password', html)

    def test_login_failure_nonexistent_email_shows_visible_error(self):
        """Login failure with unregistered email displays user-visible error banner."""
        res = self.client.post('/login', data={
            'email': 'nobody@example.com',
            'password': 'SomePassword123!'
        })
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Invalid email address or password', html)

    def test_login_failure_invalid_email_format_shows_visible_error(self):
        """Login failure with malformed email displays user-visible error banner and never silently re-renders."""
        res = self.client.post('/login', data={
            'email': 'notanemail',
            'password': 'Password123!'
        })
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Please enter a valid email address.', html)

    def test_login_failure_empty_fields_shows_visible_error(self):
        """Submitting empty fields displays user-visible errors and never silently reloads a blank form."""
        res = self.client.post('/login', data={
            'email': '',
            'password': ''
        })
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertTrue(
            'Email is required.' in html or
            'Password is required.' in html or
            'Please check the form for errors' in html
        )

    def test_deactivated_account_shows_specific_error(self):
        """Deactivated account displays clear contact support message and returns 403."""
        res = self.client.post('/login', data={
            'email': 'inactive@example.com',
            'password': 'InactivePass123!'
        })
        self.assertEqual(res.status_code, 403)
        html = res.data.decode('utf-8')
        self.assertIn('Your account has been deactivated', html)


if __name__ == '__main__':
    unittest.main()
