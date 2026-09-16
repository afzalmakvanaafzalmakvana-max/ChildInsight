import unittest
from app import create_app, db
from app.models.user import User
from app.utils.seed_data import seed_activities


class NavbarLayoutTestCase(unittest.TestCase):
    """Tests confirming navbar layout, compact spacing, System dropdown, and responsive rules."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create test users
        self.admin = User(name='Admin User', email='admin@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)

        self.teacher = User(name='Teacher Sarah', email='sarah.teacher@example.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')
        db.session.add(self.teacher)

        self.parent = User(name='Parent Mark', email='mark.parent@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)

        db.session.commit()
        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_user(self, email, password):
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def test_admin_navbar_elements_and_system_dropdown(self):
        """Confirm admin dashboard navbar contains the consolidated System dropdown and required items."""
        self.login_user('admin@example.com', 'AdminPass123!')
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Brand and badge
        self.assertIn('🌱 ChildInsight', html)
        self.assertIn('Admin Console', html)
        self.assertIn('brand-badge badge-primary', html)

        # Primary top-level navigation links
        self.assertIn('Overview', html)
        self.assertIn('User Management', html)
        self.assertIn('Categories', html)
        self.assertIn('Activities', html)
        self.assertIn('Teacher Assignments', html)

        # System dropdown component
        self.assertIn('nav-dropdown', html)
        self.assertIn('nav-dropdown-toggle', html)
        self.assertIn('adminSystemDropdown', html)
        self.assertIn('dropdown-menu', html)

        # Grouped system items
        self.assertIn('Audit Logs', html)
        self.assertIn('System Agents', html)
        self.assertIn('Content Suggestions', html)

        # User info and controls
        self.assertIn('nav-user-label', html)
        self.assertIn('Admin User', html)
        self.assertIn('Sign Out', html)
        self.assertIn('theme-toggle-btn', html)

    def test_admin_agents_inherits_standard_navbar(self):
        """Confirm admin agents page extends base_admin.html with System dropdown."""
        self.login_user('admin@example.com', 'AdminPass123!')
        res = self.client.get('/admin/agents', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Confirm standard admin brand and System dropdown are present
        self.assertIn('Admin Console', html)
        self.assertIn('nav-dropdown', html)
        self.assertIn('nav-dropdown-toggle', html)
        self.assertIn('System Agents', html)
        self.assertIn('Content Suggestions', html)
        self.assertIn('Audit Logs', html)

    def test_teacher_navbar_elements(self):
        """Confirm teacher portal navbar contains correct badge and nav-user-label."""
        self.login_user('sarah.teacher@example.com', 'TeacherPass123!')
        res = self.client.get('/teacher/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Teacher Portal', html)
        self.assertIn('nav-user-label', html)
        self.assertIn('Teacher Sarah', html)
        self.assertIn('Sign Out', html)

    def test_parent_navbar_elements(self):
        """Confirm parent portal navbar contains correct badge and nav-user-label."""
        self.login_user('mark.parent@example.com', 'ParentPass123!')
        res = self.client.get('/parent/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Parent Portal', html)
        self.assertIn('nav-user-label', html)
        self.assertIn('Parent Mark', html)
        self.assertIn('Sign Out', html)

    def test_style_css_navbar_rules(self):
        """Verify CSS file includes the compact navbar spacing, dropdown classes, and responsive breakpoints."""
        with open('app/static/css/style.css', 'r', encoding='utf-8') as f:
            css = f.read()

        # Navbar container widening
        self.assertIn('.navbar .container', css)
        self.assertIn('max-width: 1440px', css)

        # Compact spacing
        self.assertIn('.nav-links', css)
        self.assertIn('gap: 0.4rem', css)
        self.assertIn('font-size: 0.875rem', css)
        self.assertIn('padding: 0.35rem 0.6rem', css)

        # Dropdown classes
        self.assertIn('.nav-dropdown', css)
        self.assertIn('.nav-dropdown-toggle', css)
        self.assertIn('.dropdown-menu', css)
        self.assertIn('.dropdown-item', css)

        # User label truncation
        self.assertIn('.nav-user-label', css)
        self.assertIn('text-overflow: ellipsis', css)

        # Responsive media queries
        self.assertIn('@media (max-width: 1024px)', css)
        self.assertIn('@media (max-width: 768px)', css)


if __name__ == '__main__':
    unittest.main()
