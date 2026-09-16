import unittest
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.teacher_assignment import TeacherAssignment
from app.utils.seed_data import seed_activities


class AdminTableResponsivenessTestCase(unittest.TestCase):
    """Test suite verifying responsive data tables, sticky column rendering, and horizontal scroll safety."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        seed_activities()

        # Seed Admin User
        self.admin = User(name='Admin Boss', email='admin.tables@example.com', role='admin', is_active=True)
        self.admin.set_password('AdminPass123!')

        # Seed Teacher and Parent for assignments
        self.teacher = User(name='Teacher Lisa', email='teacher.lisa@example.com', role='teacher', is_active=True)
        self.teacher.set_password('TeacherPass123!')

        self.parent = User(name='Parent Mark', email='parent.mark@example.com', role='parent', is_active=True)
        self.parent.set_password('ParentPass123!')

        db.session.add_all([self.admin, self.teacher, self.parent])
        db.session.commit()

        self.child = Child(parent_id=self.parent.id, name='Timmy', age=7, grade='2nd Grade')
        db.session.add(self.child)
        db.session.commit()

        assignment = TeacherAssignment(teacher_id=self.teacher.id, child_id=self.child.id)
        db.session.add(assignment)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_admin(self):
        return self.client.post('/login', data={
            'email': 'admin.tables@example.com',
            'password': 'AdminPass123!'
        }, follow_redirects=True)

    def test_css_sticky_and_responsive_rules_exist(self):
        """Verify style.css contains critical responsive table and sticky column architecture rules."""
        res = self.client.get('/static/css/style.css')
        self.assertEqual(res.status_code, 200)
        css = res.data.decode('utf-8')

        # Scroll container rules
        self.assertIn('.table-responsive-container', css)
        self.assertIn('overflow-x: auto', css)
        self.assertIn('-webkit-overflow-scrolling: touch', css)
        self.assertIn('scrollbar-width: thin', css)

        # Separate border collapse is mandatory for sticky table headers & cells
        self.assertIn('.admin-data-table', css)
        self.assertIn('border-collapse: separate', css)

        # Sticky column rules
        self.assertIn('.admin-data-table .col-sticky', css)
        self.assertIn('position: sticky', css)
        self.assertIn('left: 0', css)
        self.assertIn('z-index: 2', css)

        # Dark mode opacity safeguarding
        self.assertIn('[data-theme="dark"] .admin-data-table .col-sticky', css)

    def test_admin_activities_table_has_sticky_title_and_merged_category(self):
        """Admin activities list renders sticky title column with full-title tooltip and reduced footprint."""
        self.login_admin()
        res = self.client.get('/admin/activities')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Verify container and table classes
        self.assertIn('table-responsive-container', html)
        self.assertIn('admin-data-table', html)

        # Verify sticky header and sticky cells
        self.assertIn('<th class="col-sticky"', html)
        self.assertIn('<td class="col-sticky"', html)

        # Verify title tooltip and readable structure
        act = Activity.query.first()
        self.assertIsNotNone(act)
        self.assertIn(f'title="{act.title}"', html)
        self.assertIn('class="admin-table-title"', html)

        # Verify Category is merged into title cell reducing horizontal footprint
        self.assertIn('Activity &amp; Category', html)
        self.assertIn(act.category.name, html)

    def test_admin_users_table_has_sticky_user_column(self):
        """Admin users list table renders sticky User column inside responsive container."""
        self.login_admin()
        res = self.client.get('/admin/users')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('table-responsive-container', html)
        self.assertIn('admin-data-table', html)
        self.assertIn('<th class="col-sticky"', html)
        self.assertIn('<td class="col-sticky"', html)
        self.assertIn('Admin Boss', html)

    def test_admin_categories_table_has_sticky_category_column(self):
        """Admin categories list table renders sticky Category column inside responsive container."""
        self.login_admin()
        res = self.client.get('/admin/categories')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('table-responsive-container', html)
        self.assertIn('admin-data-table', html)
        self.assertIn('<th class="col-sticky"', html)
        self.assertIn('<td class="col-sticky"', html)

    def test_admin_audit_logs_table_has_sticky_timestamp_column(self):
        """Admin audit logs table renders sticky timestamp column inside responsive container."""
        # Seed an audit log so the table renders
        from app.models.audit_log import AuditLog
        log_entry = AuditLog(user_id=self.admin.id, action='role_change', target_type='User', target_id=str(self.parent.id))
        db.session.add(log_entry)
        db.session.commit()

        self.login_admin()
        res = self.client.get('/admin/audit-logs')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('table-responsive-container', html)
        self.assertIn('admin-data-table', html)
        self.assertIn('<th class="col-sticky"', html)
        self.assertIn('<td class="col-sticky"', html)

    def test_admin_assignments_tables_have_sticky_columns(self):
        """Admin teacher assignments page renders sticky columns for active assignments and parent grants."""
        self.login_admin()
        res = self.client.get('/admin/assignments')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('table-responsive-container', html)
        self.assertIn('admin-data-table', html)
        self.assertIn('<th class="col-sticky"', html)
        self.assertIn('<td class="col-sticky"', html)
        self.assertIn('Teacher Lisa', html)

    def test_admin_questions_table_has_sticky_column(self):
        """Admin activity questions list renders sticky prompt column inside responsive container."""
        self.login_admin()
        act = Activity.query.first()
        res = self.client.get(f'/admin/activities/{act.id}/questions')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('table-responsive-container', html)
        self.assertIn('admin-data-table', html)
        self.assertIn('<th class="col-sticky"', html)
        self.assertIn('<td class="col-sticky"', html)


if __name__ == '__main__':
    unittest.main()
