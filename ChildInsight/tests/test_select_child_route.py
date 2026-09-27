import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category


class SelectChildRouteTestCase(unittest.TestCase):
    """
    Automated tests verifying the dedicated GET /child/select-child route:
    - Route exists and returns HTTP 200 for parents with multiple children
    - Unauthenticated visitors are redirected to /login
    - Parents with 0 children are redirected to parent dashboard with a flash notice
    - The Switch Learner button on child activities links directly to /child/select-child
    - Back navigation on select_child.html links back to parent dashboard
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create parent with multiple children
        self.parent = User(name='Parent Multiple', email='parent.multi@test.com', role='parent', is_active=True)
        self.parent.set_password('DemoPass123!')
        db.session.add(self.parent)
        db.session.commit()

        self.child1 = Child(name='Maya', age=7, parent_id=self.parent.id, preferred_language='en')
        self.child2 = Child(name='Rohan', age=9, parent_id=self.parent.id, preferred_language='hi')
        db.session.add_all([self.child1, self.child2])

        # Create parent with 0 children
        self.empty_parent = User(name='Parent Zero', email='parent.zero@test.com', role='parent', is_active=True)
        self.empty_parent.set_password('DemoPass123!')
        db.session.add(self.empty_parent)

        # Create teacher
        self.teacher = User(name='Teacher Tina', email='teacher.tina@test.com', role='teacher', is_active=True)
        self.teacher.set_password('DemoPass123!')
        db.session.add(self.teacher)

        # Create category
        self.cat = Category(name='Logic & Reasoning', slug='logic', icon='🧩', description='Puzzles')
        db.session.add(self.cat)

        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='DemoPass123!'):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def test_unauthenticated_access_redirects_to_login(self):
        """Unauthenticated GET /child/select-child redirects to /login."""
        res = self.client.get('/child/select-child')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

    def test_parent_multi_child_select_child_renders_200(self):
        """Parent with multiple children visiting /child/select-child gets HTTP 200 and sees children."""
        self._login('parent.multi@test.com')
        res = self.client.get('/child/select-child')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        self.assertIn('Maya', html)
        self.assertIn('Rohan', html)
        self.assertIn(f'/child/{self.child1.id}/activities', html)
        self.assertIn(f'/child/{self.child2.id}/activities', html)
        self.assertIn('/parent/dashboard', html)

    def test_parent_zero_children_redirects_to_dashboard(self):
        """Parent with zero children visiting /child/select-child is redirected with notice."""
        self._login('parent.zero@test.com')
        res = self.client.get('/child/select-child', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/parent/dashboard', res.headers.get('Location', ''))

    def test_teacher_redirected_from_select_child(self):
        """Teacher visiting /child/select-child is redirected to teacher dashboard."""
        self._login('teacher.tina@test.com')
        res = self.client.get('/child/select-child', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/teacher/dashboard', res.headers.get('Location', ''))

    def test_switch_learner_button_links_to_select_child(self):
        """On child activities screen, multi-child parents have a 'Switch Learner' link to /child/select-child."""
        self._login('parent.multi@test.com')
        res = self.client.get(f'/child/{self.child1.id}/activities')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        self.assertIn('/child/select-child', html)


if __name__ == '__main__':
    unittest.main()
