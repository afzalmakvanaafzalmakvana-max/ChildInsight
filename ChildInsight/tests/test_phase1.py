import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child


class Phase1TestCase(unittest.TestCase):
    """Automated test suite verifying Phase 1 Project Foundation."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # --- 1. App Factory & Blueprints ---

    def test_app_creation_and_config(self):
        """Test application factory properly sets testing configuration."""
        self.assertTrue(self.app.config['TESTING'])
        self.assertEqual(self.app.config['SQLALCHEMY_DATABASE_URI'], 'sqlite:///:memory:')

    def test_blueprints_registered(self):
        """Ensure all required blueprints are registered."""
        blueprint_names = self.app.blueprints.keys()
        for expected in ['auth', 'parent', 'teacher', 'child', 'admin', 'api']:
            self.assertIn(expected, blueprint_names)

    # --- 2. User & Child Models ---

    def test_password_hashing(self):
        """Test Werkzeug password hashing and verification."""
        user = User(name='Test User', email='test@example.com', role='parent')
        user.set_password('Secret123!')
        db.session.add(user)
        db.session.commit()

        self.assertNotEqual(user.password_hash, 'Secret123!')
        self.assertTrue(user.check_password('Secret123!'))
        self.assertFalse(user.check_password('WrongPassword'))

    def test_user_roles(self):
        """Test user role identification properties."""
        parent = User(name='Parent', email='parent@example.com', role='parent')
        teacher = User(name='Teacher', email='teacher@example.com', role='teacher')
        admin = User(name='Admin', email='admin@example.com', role='admin')
        child = User(name='Child', email='child@example.com', role='child')

        self.assertTrue(parent.is_parent)
        self.assertTrue(teacher.is_teacher)
        self.assertTrue(admin.is_admin)
        self.assertTrue(child.is_child)

    def test_child_model_and_relationship(self):
        """Test child creation linked to parent."""
        parent = User(name='Parent User', email='parent_child@example.com', role='parent')
        parent.set_password('Secret123!')
        db.session.add(parent)
        db.session.commit()

        child = Child(
            parent_id=parent.id,
            name='Leo',
            age=7,
            grade='2nd Grade',
            preferred_language='English'
        )
        db.session.add(child)
        db.session.commit()

        self.assertEqual(child.parent.email, 'parent_child@example.com')
        self.assertEqual(parent.children.count(), 1)
        self.assertEqual(parent.children.first().name, 'Leo')

    # --- 3. Authentication & Auth Views ---

    def test_landing_page(self):
        """Test public landing page loads with responsible-use notice."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ChildInsight', response.data)
        self.assertIn(b'Responsible-Use', response.data)

    def test_user_registration(self):
        """Test new user registration flow."""
        response = self.client.post('/register', data={
            'name': 'New Parent',
            'email': 'newparent@example.com',
            'role': 'parent',
            'password': 'SecurePassword123',
            'confirm_password': 'SecurePassword123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your account has been created successfully', response.data)

        user = User.query.filter_by(email='newparent@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, 'New Parent')
        self.assertEqual(user.role, 'parent')
        self.assertTrue(user.check_password('SecurePassword123'))

    def test_duplicate_registration_prevented(self):
        """Test duplicate email registration rejection."""
        user = User(name='Existing', email='exists@example.com', role='parent')
        user.set_password('Password123')
        db.session.add(user)
        db.session.commit()

        response = self.client.post('/register', data={
            'name': 'Duplicate',
            'email': 'exists@example.com',
            'role': 'parent',
            'password': 'Password123',
            'confirm_password': 'Password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'An account with this email address already exists', response.data)

    def test_login_and_logout(self):
        """Test login with valid credentials and subsequent logout."""
        user = User(name='Login User', email='login@example.com', role='parent')
        user.set_password('Password123')
        db.session.add(user)
        db.session.commit()

        # Valid login redirects to parent dashboard
        response = self.client.post('/login', data={
            'email': 'login@example.com',
            'password': 'Password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Parent Portal', response.data)

        # Logout redirects to index
        logout_response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertIn(b'You have been signed out successfully', logout_response.data)

    def test_invalid_login(self):
        """Test login rejection with bad password."""
        user = User(name='Valid User', email='valid@example.com', role='parent')
        user.set_password('Password123')
        db.session.add(user)
        db.session.commit()

        response = self.client.post('/login', data={
            'email': 'valid@example.com',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email address or password', response.data)

    def test_inactive_user_login(self):
        """Test deactivated account is denied login."""
        user = User(name='Inactive', email='inactive@example.com', role='parent', is_active=False)
        user.set_password('Password123')
        db.session.add(user)
        db.session.commit()

        response = self.client.post('/login', data={
            'email': 'inactive@example.com',
            'password': 'Password123'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Your account has been deactivated', response.data)

    # --- 4. Role-based Route Protection ---

    def test_role_protected_routes(self):
        """Test that unauthenticated requests to protected dashboards are redirected."""
        response = self.client.get('/parent/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

        response = self.client.get('/teacher/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_role_cross_access_forbidden(self):
        """Test that a parent cannot access the admin dashboard."""
        parent = User(name='Parent User', email='parent_cross@example.com', role='parent')
        parent.set_password('Password123')
        db.session.add(parent)
        db.session.commit()

        # Login as parent
        self.client.post('/login', data={'email': 'parent_cross@example.com', 'password': 'Password123'})

        # Attempt to access admin dashboard
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Access Forbidden', response.data)

    # --- 5. API Endpoints ---

    def test_api_health_endpoint(self):
        """Test API health check returns expected status."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'healthy')
        self.assertEqual(json_data['service'], 'ChildInsight API')

    def test_api_auth_status(self):
        """Test auth status reports anonymous before login and authenticated after."""
        anon_resp = self.client.get('/api/auth/status')
        self.assertEqual(anon_resp.status_code, 200)
        self.assertFalse(anon_resp.get_json()['authenticated'])

        user = User(name='API User', email='api_user@example.com', role='teacher')
        user.set_password('Password123')
        db.session.add(user)
        db.session.commit()

        self.client.post('/login', data={'email': 'api_user@example.com', 'password': 'Password123'})
        auth_resp = self.client.get('/api/auth/status')
        self.assertEqual(auth_resp.status_code, 200)
        data = auth_resp.get_json()
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['user']['role'], 'teacher')

    # --- 6. Custom Error Handlers ---

    def test_404_error_page(self):
        """Test custom 404 handler returns friendly page."""
        response = self.client.get('/non-existent-page-test-404')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Page Not Found', response.data)

    def test_500_error_page(self):
        """Test custom 500 handler returns friendly page matching rules.md."""
        from flask import abort

        @self.app.route('/force-500-test')
        def force_500():
            abort(500)

        response = self.client.get('/force-500-test')
        self.assertEqual(response.status_code, 500)
        self.assertIn(b'Something went wrong. Please try again.', response.data)


if __name__ == '__main__':
    unittest.main()
