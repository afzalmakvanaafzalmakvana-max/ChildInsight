import unittest
import re
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.utils.seed_data import seed_activities


class ChildBackNavigationSecurityTestCase(unittest.TestCase):
    """Verifies that navigation from child-facing activity screens never leads to Admin routes,

    that role transitions behave cleanly without session pollution, and that RBAC strictly
    enforces 403 Forbidden on all /admin/* endpoints for non-admin accounts.
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed categories & activities
        seed_activities()

        # Create test users across all roles
        self.admin = User(name='Admin Charlie', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')

        self.parent = User(name='Parent Alice', email='alice@example.com', role='parent')
        self.parent.set_password('ParentPass123!')

        self.teacher = User(name='Teacher Davis', email='davis@example.com', role='teacher')
        self.teacher.set_password('TeacherPass123!')

        self.child_user = User(name='Child Leo User', email='child@example.com', role='child')
        self.child_user.set_password('ChildPass123!')

        db.session.add_all([self.admin, self.parent, self.teacher, self.child_user])
        db.session.commit()

        # Create child profile
        self.child = Child(
            id=self.child_user.id,
            parent_id=self.parent.id,
            name='Leo',
            age=6,
            grade='1st Grade',
            preferred_language='English'
        )
        db.session.add(self.child)
        db.session.commit()

        # Fetch seeded activity
        self.activity = Activity.query.first()
        self.category = Category.query.first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=False)

    def _get_all_links(self, html):
        return re.findall(r'<a\s+(?:[^>]*?\s+)?href=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)

    def test_admin_navigate_signout_login_child_back_navigation_flow(self):
        """Simulate exact sequence:

        1. Log in as admin
        2. Navigate admin pages
        3. Sign out
        4. Log in as parent
        5. Navigate to child activity screens
        6. Traverse all 'back' links (player -> activity_list -> categories -> parent dashboard)
        7. Confirm no step ever lands on or links to an admin route.
        """
        # Step 1: Log in as admin
        resp = self._login('admin@example.com', 'AdminPass123!')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin', resp.headers['Location'])

        # Step 2: Navigate admin pages
        admin_pages = ['/admin/dashboard', '/admin/users', '/admin/audit-logs']
        for page in admin_pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200)

        # Step 3: Sign out
        logout_resp = self.client.get('/auth/logout', follow_redirects=True)
        self.assertEqual(logout_resp.status_code, 200)

        # Step 4: Log in as parent
        resp = self._login('alice@example.com', 'ParentPass123!')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/parent/dashboard', resp.headers['Location'])

        # Step 5: Start playing an activity
        player_url = f'/child/{self.child.id}/play/{self.activity.id}'
        player_resp = self.client.get(player_url)
        self.assertEqual(player_resp.status_code, 200)

        player_links = self._get_all_links(player_resp.data.decode('utf-8'))
        for link in player_links:
            self.assertFalse(link.startswith('/admin'), f"Player screen contains admin link: {link}")

        # Step 6a: Click 'Back to Activities' (calls abandon route)
        abandon_url = f'/child/{self.child.id}/play/{self.activity.id}/abandon'
        abandon_resp = self.client.get(abandon_url, follow_redirects=False)
        self.assertEqual(abandon_resp.status_code, 302)
        # Verify abandon redirects to activity list, NOT admin
        self.assertNotIn('/admin', abandon_resp.headers['Location'])
        self.assertIn(f'/child/{self.child.id}/category/', abandon_resp.headers['Location'])

        # Step 6b: On activity list, inspect links and click 'Back to Categories'
        act_list_resp = self.client.get(abandon_resp.headers['Location'])
        self.assertEqual(act_list_resp.status_code, 200)
        list_links = self._get_all_links(act_list_resp.data.decode('utf-8'))
        for link in list_links:
            self.assertFalse(link.startswith('/admin'), f"Activity list screen contains admin link: {link}")

        categories_hub_url = f'/child/{self.child.id}/activities'
        self.assertTrue(any(categories_hub_url in link for link in list_links))

        # Step 6c: On categories hub, inspect links
        cat_resp = self.client.get(categories_hub_url)
        self.assertEqual(cat_resp.status_code, 200)
        cat_links = self._get_all_links(cat_resp.data.decode('utf-8'))
        for link in cat_links:
            self.assertFalse(link.startswith('/admin'), f"Categories hub screen contains admin link: {link}")

        # For parent, back link goes to parent.dashboard
        self.assertTrue(any('/parent/dashboard' in link for link in cat_links))

        # Step 6d: Follow back to parent dashboard
        parent_dash_resp = self.client.get('/parent/dashboard')
        self.assertEqual(parent_dash_resp.status_code, 200)

        # Confirm parent dashboard has NO links to admin
        parent_links = self._get_all_links(parent_dash_resp.data.decode('utf-8'))
        for link in parent_links:
            self.assertFalse(link.startswith('/admin'), f"Parent dashboard contains admin link: {link}")

    def test_child_user_back_navigation_stays_in_child_zone(self):
        """When logged in as a child, back navigation should remain in the child experience

        and never expose admin links or routes.
        """
        self._login('child@example.com', 'ChildPass123!')

        # 1. Activities category hub
        resp = self.client.get(f'/child/{self.child.id}/activities')
        self.assertEqual(resp.status_code, 200)
        links = self._get_all_links(resp.data.decode('utf-8'))
        for link in links:
            self.assertFalse(link.startswith('/admin'), f"Child activity screen contains admin link: {link}")

        # 'Back to Home' links to /child/home
        self.assertTrue(any('/child/home' in link for link in links))

        # 2. Clicking /child/home as child redirects to categories_hub
        home_resp = self.client.get('/child/home', follow_redirects=False)
        self.assertEqual(home_resp.status_code, 302)
        self.assertEqual(home_resp.headers['Location'], f'/child/{self.child.id}/activities')

        # 3. Base child hub /child/home for unauthenticated visitor has no admin links
        self.client.get('/auth/logout')
        guest_resp = self.client.get('/child/home')
        self.assertEqual(guest_resp.status_code, 200)
        guest_links = self._get_all_links(guest_resp.data.decode('utf-8'))
        for link in guest_links:
            self.assertFalse(link.startswith('/admin'), f"Guest child hub contains admin link: {link}")
            self.assertFalse(link == '/', f"Guest child hub has misleading back link to root: {link}")

    def test_relogin_without_explicit_signout_clears_admin_session(self):
        """Simulate testing artifact: tester logged into Admin, then submits login form

        with Parent or Child credentials without first clicking Sign Out.
        The application must cleanly log out the admin and log in the new user,
        redirecting to the role-appropriate dashboard instead of staying trapped in admin.
        """
        # Log in as admin
        self._login('admin@example.com', 'AdminPass123!')

        # Now submit login with parent credentials
        resp = self.client.post('/auth/login', data={
            'email': 'alice@example.com',
            'password': 'ParentPass123!'
        }, follow_redirects=False)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers['Location'], '/parent/dashboard')

        # Verify current session is parent, NOT admin
        dash_resp = self.client.get('/parent/dashboard')
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn('Parent Alice', dash_resp.data.decode('utf-8'))

    def test_strict_rbac_blocks_child_from_all_admin_endpoints(self):
        """Verify that role-based access control strictly returns 403 Forbidden for a child user

        across all admin routes.
        """
        self._login('child@example.com', 'ChildPass123!')

        admin_routes = [
            ('/admin/dashboard', 'GET'),
            ('/admin/users', 'GET'),
            ('/admin/assignments', 'GET'),
            ('/admin/audit-logs', 'GET'),
            ('/admin/categories', 'GET'),
            ('/admin/activities', 'GET'),
            ('/admin/agents', 'GET'),
            ('/admin/content-suggestions', 'GET'),
            ('/admin/agents/run', 'POST'),
            ('/admin/content-suggestions/run', 'POST'),
        ]

        for route, method in admin_routes:
            if method == 'GET':
                resp = self.client.get(route)
            else:
                resp = self.client.post(route)
            self.assertEqual(
                resp.status_code, 403,
                f"Child user was not blocked with 403 on {method} {route} (got {resp.status_code})"
            )

    def test_strict_rbac_blocks_parent_from_all_admin_endpoints(self):
        """Verify that role-based access control strictly returns 403 Forbidden for a parent user

        across all admin routes.
        """
        self._login('alice@example.com', 'ParentPass123!')

        admin_routes = [
            ('/admin/dashboard', 'GET'),
            ('/admin/users', 'GET'),
            ('/admin/assignments', 'GET'),
            ('/admin/audit-logs', 'GET'),
            ('/admin/categories', 'GET'),
            ('/admin/activities', 'GET'),
            ('/admin/agents', 'GET'),
            ('/admin/content-suggestions', 'GET'),
            ('/admin/agents/run', 'POST'),
            ('/admin/content-suggestions/run', 'POST'),
        ]

        for route, method in admin_routes:
            if method == 'GET':
                resp = self.client.get(route)
            else:
                resp = self.client.post(route)
            self.assertEqual(
                resp.status_code, 403,
                f"Parent user was not blocked with 403 on {method} {route} (got {resp.status_code})"
            )


if __name__ == '__main__':
    unittest.main()
