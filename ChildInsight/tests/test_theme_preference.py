import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category
from app.utils.seed_data import seed_activities


class ThemePreferenceTestCase(unittest.TestCase):
    """Automated tests confirming light/dark theme toggle and persistence."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create test parent user
        self.parent = User(name='Theme Parent', email='theme.parent@example.com', role='parent', is_active=True)
        self.parent.set_password('Password123!')
        db.session.add(self.parent)
        db.session.commit()

        # Create child for parent
        self.child = Child(name='Theme Child', age=7, grade='2nd', parent_id=self.parent.id)
        db.session.add(self.child)
        db.session.commit()

        # Seed categories for child navigation tests
        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_parent(self):
        return self.client.post('/auth/login', data={
            'email': 'theme.parent@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)

    def test_default_theme_preference_is_light(self):
        """Confirm a newly registered user defaults to light theme."""
        user = db.session.get(User, self.parent.id)
        self.assertEqual(user.theme_preference, 'light')

    def test_theme_api_get_and_post(self):
        """Confirm GET and POST /api/user/theme updates DB and returns cookie."""
        self.login_parent()

        # GET initial theme
        res = self.client.get('/api/user/theme')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['theme'], 'light')

        # POST invalid theme
        bad_res = self.client.post('/api/user/theme', json={'theme': 'neon'})
        self.assertEqual(bad_res.status_code, 400)

        # POST dark theme
        post_res = self.client.post('/api/user/theme', json={'theme': 'dark'})
        self.assertEqual(post_res.status_code, 200)
        data = post_res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['theme'], 'dark')
        self.assertTrue(data['persisted_to_db'])

        # Verify DB updated
        user = db.session.get(User, self.parent.id)
        self.assertEqual(user.theme_preference, 'dark')

        # Verify cookie set
        cookies = post_res.headers.getlist('Set-Cookie')
        self.assertTrue(any('childinsight_theme=dark' in c for c in cookies))

    def test_saved_theme_preference_applied_on_next_login(self):
        """Confirm user's saved theme preference (dark) is rendered on next login."""
        # 1. Log in and switch to dark mode
        self.login_parent()
        update_res = self.client.post('/api/user/theme', json={'theme': 'dark'})
        self.assertEqual(update_res.status_code, 200)

        # 2. Log out
        self.client.get('/auth/logout', follow_redirects=True)

        # 3. Log in afresh
        login_res = self.login_parent()
        self.assertEqual(login_res.status_code, 200)

        # 4. Fetch dashboard HTML and confirm data-theme="dark" attribute
        dash_res = self.client.get('/parent/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        html = dash_res.get_data(as_text=True)
        self.assertIn('data-theme="dark"', html)

    def test_theme_toggle_back_to_light_applied_on_next_login(self):
        """Confirm switching back to light mode is persisted and rendered on next login."""
        # 1. Set to dark first
        self.login_parent()
        self.client.post('/api/user/theme', json={'theme': 'dark'})

        # 2. Switch back to light
        toggle_res = self.client.post('/api/user/theme', json={'theme': 'light'})
        self.assertEqual(toggle_res.status_code, 200)

        # 3. Log out and log back in
        self.client.get('/auth/logout', follow_redirects=True)
        self.login_parent()

        # 4. Confirm data-theme="light" rendered
        dash_res = self.client.get('/parent/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        html = dash_res.get_data(as_text=True)
        self.assertIn('data-theme="light"', html)

    def test_child_interface_isolated_from_dark_mode(self):
        """Confirm child screens stay strictly in bright light mode without toggle button."""
        # Parent has dark mode preference
        self.login_parent()
        self.client.post('/api/user/theme', json={'theme': 'dark'})

        # Visit child hub
        child_res = self.client.get(f'/child/{self.child.id}/activities')
        self.assertEqual(child_res.status_code, 200)
        child_html = child_res.get_data(as_text=True)

        # Child view must have child-theme class
        self.assertIn('child-theme', child_html)

        # Child view must NOT contain the theme toggle button
        self.assertNotIn('id="theme-toggle-btn"', child_html)

    def test_anonymous_theme_cookie_applied(self):
        """Confirm unauthenticated users can set theme via cookie and see it applied."""
        # Anonymous POST to /api/user/theme
        anon_res = self.client.post('/api/user/theme', json={'theme': 'dark'})
        self.assertEqual(anon_res.status_code, 200)
        self.assertFalse(anon_res.get_json()['persisted_to_db'])

        # GET login page with cookie
        login_page_res = self.client.get('/auth/login')
        self.assertEqual(login_page_res.status_code, 200)
        html = login_page_res.get_data(as_text=True)
        self.assertIn('data-theme="dark"', html)


if __name__ == '__main__':
    unittest.main()
