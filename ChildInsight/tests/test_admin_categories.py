import unittest
from app import create_app, db
from app.models.user import User
from app.models.activity import Category, Activity
from app.models.audit_log import AuditLog
from app.utils.seed_data import seed_activities


class AdminCategoryManagementTestCase(unittest.TestCase):
    """Automated tests verifying administrative category management, safeguards, and access controls."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create admin user
        self.admin = User(name='Admin User', email='admin.test@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)

        # Create non-admin parent user
        self.parent = User(name='Parent User', email='parent.test@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')
        db.session.add(self.parent)

        # Create non-admin teacher user
        self.teacher = User(name='Teacher User', email='teacher.test@example.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')
        db.session.add(self.teacher)

        db.session.commit()

        # Seed categories & activities
        seed_activities()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_user(self, email, password):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def test_non_admin_access_forbidden(self):
        """Unauthenticated and non-admin users cannot access category management endpoints."""
        endpoints = [
            ('/admin/categories', 'GET'),
            ('/admin/categories/new', 'GET'),
            ('/admin/categories/new', 'POST'),
            ('/admin/categories/1/edit', 'GET'),
            ('/admin/categories/1/edit', 'POST'),
            ('/admin/categories/1/delete', 'POST')
        ]

        # 1. Unauthenticated -> redirects to login
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url, data={})
            self.assertEqual(res.status_code, 302, f"Unauthenticated request to {url} should redirect")
            self.assertIn('/auth/login', res.headers.get('Location', ''))

        # 2. Parent -> 403 Forbidden
        self.login_user('parent.test@example.com', 'ParentPass123!')
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url, data={})
            self.assertEqual(res.status_code, 403, f"Parent request to {url} should be forbidden (403)")
        self.client.get('/auth/logout')

        # 3. Teacher -> 403 Forbidden
        self.login_user('teacher.test@example.com', 'TeacherPass123!')
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url, data={})
            self.assertEqual(res.status_code, 403, f"Teacher request to {url} should be forbidden (403)")

    def test_categories_list_displays_categories_and_counts(self):
        """Admin can view categories table with active activity counts."""
        self.login_user('admin.test@example.com', 'AdminPass123!')
        res = self.client.get('/admin/categories')
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        self.assertIn("Activity Categories", html)
        self.assertIn("Visual Learning", html)
        self.assertIn("Logic", html)
        self.assertIn("Numbers", html)
        self.assertIn("Language", html)
        self.assertIn("Memory", html)
        self.assertIn("activities", html)

    def test_create_category_success(self):
        """Admin creates a new category; slug is generated, audit log is written."""
        self.login_user('admin.test@example.com', 'AdminPass123!')

        res = self.client.post('/admin/categories/new', data={
            'name': 'Creative Arts',
            'description': 'Exercises exploring visual drawing, patterns, and musical rhythms.',
            'icon': '🎨'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("Category &#39;Creative Arts&#39; created successfully.", html)

        # Verify in DB
        cat = Category.query.filter_by(name='Creative Arts').first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.slug, 'creative-arts')
        self.assertEqual(cat.icon, '🎨')
        self.assertEqual(cat.activities.count(), 0)

        # Verify audit log
        log = AuditLog.query.filter_by(action='create_category', target_id=cat.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user_id, self.admin.id)

    def test_create_duplicate_category_fails(self):
        """Creating a category with an existing name fails with validation error."""
        self.login_user('admin.test@example.com', 'AdminPass123!')

        initial_count = Category.query.count()
        res = self.client.post('/admin/categories/new', data={
            'name': 'Visual Learning',  # Already exists
            'description': 'Duplicate category test.',
            'icon': '👁️'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("already exists", html)
        self.assertEqual(Category.query.count(), initial_count)

    def test_edit_category_success(self):
        """Admin can edit an existing category's name, description, and icon."""
        self.login_user('admin.test@example.com', 'AdminPass123!')
        cat = Category.query.filter_by(slug='visual').first()
        self.assertIsNotNone(cat)

        res = self.client.post(f'/admin/categories/{cat.id}/edit', data={
            'name': 'Visual Learning & Perception',
            'description': 'Updated cognitive domain description for spatial and visual matching.',
            'icon': '✨'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("updated successfully", html)

        # Reload from DB
        db.session.refresh(cat)
        self.assertEqual(cat.name, 'Visual Learning & Perception')
        self.assertEqual(cat.icon, '✨')
        self.assertIn('spatial and visual matching', cat.description)

        # Audit log check
        log = AuditLog.query.filter_by(action='edit_category', target_id=cat.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user_id, self.admin.id)

    def test_delete_category_blocked_when_activities_exist(self):
        """Attempting to delete a category with linked activities is blocked to protect data integrity."""
        self.login_user('admin.test@example.com', 'AdminPass123!')
        cat = Category.query.filter_by(slug='logic').first()
        self.assertIsNotNone(cat)
        act_count = cat.activities.count()
        self.assertGreater(act_count, 0)

        initial_cat_count = Category.query.count()

        res = self.client.post(f'/admin/categories/{cat.id}/delete', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        self.assertIn("Cannot delete category", html)
        self.assertIn(f"contains {act_count} linked", html)
        self.assertIn("data integrity", html)

        # Confirm category still exists in DB
        self.assertEqual(Category.query.count(), initial_cat_count)
        still_exists = Category.query.filter_by(id=cat.id).first()
        self.assertIsNotNone(still_exists)

    def test_delete_empty_category_succeeds(self):
        """Deleting a category with zero linked activities succeeds."""
        self.login_user('admin.test@example.com', 'AdminPass123!')

        # Create an empty category directly
        empty_cat = Category(
            name='Temporary Category',
            slug='temporary-category',
            icon='🗑️',
            description='To be deleted.'
        )
        db.session.add(empty_cat)
        db.session.commit()
        cat_id = empty_cat.id

        self.assertEqual(empty_cat.activities.count(), 0)

        res = self.client.post(f'/admin/categories/{cat_id}/delete', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = res.data.decode('utf-8')
        self.assertIn("deleted successfully", html)

        # Confirm removed from DB
        deleted = Category.query.filter_by(id=cat_id).first()
        self.assertIsNone(deleted)

        # Confirm audit log recorded
        log = AuditLog.query.filter_by(action='delete_category', target_id=cat_id).first()
        self.assertIsNotNone(log)


if __name__ == '__main__':
    unittest.main()
