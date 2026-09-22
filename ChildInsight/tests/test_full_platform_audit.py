import unittest
import re
from io import BytesIO
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.child_teacher_access import ChildTeacherAccess
from app.models.teacher_assignment import TeacherAssignment
from app.models.recommendation import Recommendation
from app.models.session import ActivitySession
from app.utils.seed_data import seed_activities


class FullPlatformAuditTestCase(unittest.TestCase):
    """Exhaustive, rigorous platform audit covering every role journey:

    - Child (EN/HI categories, gameplay, hints, answers, skip, results, back navigation)
    - Parent (register, login, child CRUD, dashboard, recommendations, progress, export PDF/CSV, teacher invite/revoke, notifications)
    - Teacher (login, dashboard, students, access requests accept/decline, student detail, assign activity, assignments)
    - Admin (dashboard, users, categories, activities, AI draft, audit logs, Action Center, System Agents, Assistant chat EN/HI, agent run)
    - Access Control Matrix (RBAC enforcement, data isolation, unauthenticated redirects)
    """

    def setUp(self):
        self.app = create_app('testing')
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed categories & activities
        seed_activities()

        # Create Admin
        self.admin = User(name='Platform Admin', email='admin@childinsight.test', role='admin')
        self.admin.set_password('AdminPass123!')

        # Create Parent 1 (Alice) with 2 children (EN & HI)
        self.parent1 = User(name='Parent Alice', email='alice@childinsight.test', role='parent')
        self.parent1.set_password('ParentPass123!')

        # Create Parent 2 (Bob) with 1 child
        self.parent2 = User(name='Parent Bob', email='bob@childinsight.test', role='parent')
        self.parent2.set_password('ParentPass123!')

        # Create Teacher (Davis)
        self.teacher = User(name='Teacher Davis', email='davis@childinsight.test', role='teacher')
        self.teacher.set_password('TeacherPass123!')

        db.session.add_all([self.admin, self.parent1, self.parent2, self.teacher])
        db.session.commit()

        # Children
        self.child_en = Child(
            parent_id=self.parent1.id,
            name='Leo English',
            age=7,
            grade='2nd Grade',
            preferred_language='English'
        )
        self.child_hi = Child(
            parent_id=self.parent1.id,
            name='Aarav Hindi',
            age=8,
            grade='3rd Grade',
            preferred_language='Hindi'
        )
        self.child_other = Child(
            parent_id=self.parent2.id,
            name='Maya BobChild',
            age=6,
            grade='1st Grade',
            preferred_language='English'
        )
        db.session.add_all([self.child_en, self.child_hi, self.child_other])
        db.session.commit()

        # Assign Teacher to child_en
        self.teacher_grant = ChildTeacherAccess(
            child_id=self.child_en.id,
            teacher_id=self.teacher.id,
            invited_email=self.teacher.email,
            status=ChildTeacherAccess.STATUS_ACTIVE,
            requested_by_parent_id=self.parent1.id
        )
        db.session.add(self.teacher_grant)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password):
        return self.client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)

    def _logout(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    # -------------------------------------------------------------
    # 1. Child Journey Tests
    # -------------------------------------------------------------
    def test_child_journey_english_and_hindi(self):
        """Audit child views: guest home, category hub (EN & HI), activity list, gameplay, hint, answer, skip, results."""
        # Guest home
        res = self.client.get('/child/home')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'learning adventure', res.data.lower())

        # Login as Parent 1 to authorize child access
        self._login('alice@childinsight.test', 'ParentPass123!')

        # 1.1 Category Hub - English
        res = self.client.get(f'/child/{self.child_en.id}/activities')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Visual Learning', res.data)
        self.assertIn(b'Logic', res.data)

        # 1.2 Category Hub - Hindi
        res = self.client.get(f'/child/{self.child_hi.id}/activities')
        self.assertEqual(res.status_code, 200)
        html_hi = res.data.decode('utf-8')
        # Check Devanagari presence
        self.assertTrue(bool(re.search(r'[\u0900-\u097F]', html_hi)))

        # 1.3 Category Activity List
        cat = Category.query.first()
        res = self.client.get(f'/child/{self.child_en.id}/category/{cat.id}')
        self.assertEqual(res.status_code, 200)

        # 1.4 Play Activity
        act = Activity.query.filter_by(category_id=cat.id, is_active=True).first()
        self.assertIsNotNone(act)
        res = self.client.get(f'/child/{self.child_en.id}/play/{act.id}')
        self.assertEqual(res.status_code, 200)

        # 1.5 Hint (POST)
        first_q = act.questions.first()
        res = self.client.post(
            f'/child/{self.child_en.id}/play/{act.id}/hint',
            data={'question_id': first_q.id, 'q_idx': 0},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(res.status_code, 200)
        json_hint = res.get_json()
        self.assertEqual(json_hint['status'], 'ok')
        self.assertTrue(len(json_hint['hint']) > 0)

        # 1.6 Submit Answer
        res = self.client.post(f'/child/{self.child_en.id}/play/{act.id}/answer', data={
            'question_id': first_q.id,
            'selected_answer': first_q.correct_answer,
            'q_idx': 0
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'feedback', res.data.lower())

        # 1.7 Skip Question
        second_q = act.questions.offset(1).first()
        if second_q:
            res = self.client.post(f'/child/{self.child_en.id}/play/{act.id}/skip', data={
                'question_id': second_q.id,
                'q_idx': 1
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        # 1.8 Results Screen
        res = self.client.get(f'/child/{self.child_en.id}/play/{act.id}/results')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'High Five', res.data)

    def test_child_back_navigation_links(self):
        """Audit that all back navigation links on child screens are safe and functional."""
        self._login('alice@childinsight.test', 'ParentPass123!')
        cat = Category.query.first()
        act = Activity.query.filter_by(category_id=cat.id).first()

        screens = [
            f'/child/{self.child_en.id}/activities',
            f'/child/{self.child_en.id}/category/{cat.id}',
            f'/child/{self.child_en.id}/play/{act.id}',
            f'/child/{self.child_en.id}/play/{act.id}/results'
        ]

        for screen in screens:
            res = self.client.get(screen)
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')
            links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)
            for link in links:
                if 'back' in link.lower() or 'dashboard' in link.lower() or 'activities' in link.lower():
                    # Must never point to admin
                    self.assertNotIn('/admin', link)

    # -------------------------------------------------------------
    # 2. Parent Journey Tests
    # -------------------------------------------------------------
    def test_parent_journey(self):
        """Audit full parent lifecycle: register, add child, edit child, dashboard, recommendations, progress, export PDF/CSV, teacher invite/revoke, notifications."""
        # 2.1 Register new parent
        reg_res = self.client.post('/auth/register', data={
            'name': 'New Parent Clara',
            'email': 'clara@childinsight.test',
            'password': 'ClaraPassword123!',
            'confirm_password': 'ClaraPassword123!',
            'role': 'parent'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b'created successfully', reg_res.data.lower())

        # 2.2 Login
        login_res = self._login('clara@childinsight.test', 'ClaraPassword123!')
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Parent Dashboard', login_res.data)

        # 2.3 Add Child
        add_res = self.client.post('/parent/children/new', data={
            'name': 'Oliver ClaraChild',
            'age': 6,
            'grade': 'Kindergarten',
            'preferred_language': 'English'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        self.assertIn(b'Oliver ClaraChild', add_res.data)

        clara_user = User.query.filter_by(email='clara@childinsight.test').first()
        oliver = Child.query.filter_by(parent_id=clara_user.id).first()
        self.assertIsNotNone(oliver)

        # 2.4 Edit Child
        edit_res = self.client.post(f'/parent/children/{oliver.id}/edit', data={
            'name': 'Oliver ClaraChild Updated',
            'age': 7,
            'grade': '1st Grade',
            'preferred_language': 'Hindi'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        self.assertIn(b'Oliver ClaraChild Updated', edit_res.data)

        # 2.5 View Recommendations
        rec_res = self.client.get(f'/parent/recommendations?child_id={oliver.id}')
        self.assertEqual(rec_res.status_code, 200)

        # 2.6 View Progress Reports
        prog_res = self.client.get(f'/parent/progress-reports?child_id={oliver.id}')
        self.assertEqual(prog_res.status_code, 200)

        # 2.7 Export PDF
        pdf_res = self.client.get(f'/parent/children/{oliver.id}/report/pdf')
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, 'application/pdf')

        # 2.8 Export CSV
        csv_res = self.client.get(f'/parent/children/{oliver.id}/report/csv')
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn('text/csv', csv_res.mimetype)

        # 2.9 Invite Teacher
        invite_res = self.client.post(f'/parent/children/{oliver.id}/share-teacher', data={
            'teacher_email': self.teacher.email
        }, follow_redirects=True)
        self.assertEqual(invite_res.status_code, 200)

        grant = ChildTeacherAccess.query.filter_by(child_id=oliver.id, teacher_id=self.teacher.id).first()
        self.assertIsNotNone(grant)

        # 2.10 Revoke Teacher Access
        revoke_res = self.client.post(
            f'/parent/children/{oliver.id}/teacher-access/{grant.id}/revoke',
            follow_redirects=True
        )
        self.assertEqual(revoke_res.status_code, 200)
        grant_revoked = db.session.get(ChildTeacherAccess, grant.id)
        self.assertEqual(grant_revoked.status, ChildTeacherAccess.STATUS_REVOKED)

        # 2.11 Notifications API
        notif_res = self.client.get('/api/notifications')
        self.assertEqual(notif_res.status_code, 200)
        self.assertIn('notifications', notif_res.get_json())

    # -------------------------------------------------------------
    # 3. Teacher Journey Tests
    # -------------------------------------------------------------
    def test_teacher_journey(self):
        """Audit teacher lifecycle: login, dashboard, student directory, access requests accept/decline, student detail, assign activity, assignments hub."""
        # 3.1 Login
        res = self._login('davis@childinsight.test', 'TeacherPass123!')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'educator workspace', res.data.lower())

        # 3.2 View Students Directory
        res = self.client.get('/teacher/students')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Leo English', res.data)

        # 3.3 Accept Access Request
        pending_grant = ChildTeacherAccess(
            child_id=self.child_hi.id,
            teacher_id=self.teacher.id,
            invited_email=self.teacher.email,
            status=ChildTeacherAccess.STATUS_PENDING_APPROVAL,
            requested_by_parent_id=self.parent1.id
        )
        db.session.add(pending_grant)
        db.session.commit()

        accept_res = self.client.post(f'/teacher/access-requests/{pending_grant.id}/accept', follow_redirects=True)
        self.assertEqual(accept_res.status_code, 200)
        updated_grant = db.session.get(ChildTeacherAccess, pending_grant.id)
        self.assertEqual(updated_grant.status, ChildTeacherAccess.STATUS_ACTIVE)

        # 3.4 Decline Access Request
        pending_decline = ChildTeacherAccess(
            child_id=self.child_other.id,
            teacher_id=self.teacher.id,
            invited_email=self.teacher.email,
            status=ChildTeacherAccess.STATUS_PENDING_APPROVAL,
            requested_by_parent_id=self.parent2.id
        )
        db.session.add(pending_decline)
        db.session.commit()

        decline_res = self.client.post(f'/teacher/access-requests/{pending_decline.id}/decline', follow_redirects=True)
        self.assertEqual(decline_res.status_code, 200)
        declined_grant = db.session.get(ChildTeacherAccess, pending_decline.id)
        self.assertEqual(declined_grant.status, ChildTeacherAccess.STATUS_DECLINED)

        # 3.5 Student Detail Report
        res = self.client.get(f'/teacher/students/{self.child_en.id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Leo English', res.data)

        # 3.6 Assign Activity
        act = Activity.query.filter_by(is_active=True).first()
        assign_res = self.client.post(f'/teacher/students/{self.child_en.id}/assign-activity', data={
            'activity_id': act.id,
            'note': 'Please practice this logic challenge.'
        }, follow_redirects=True)
        self.assertEqual(assign_res.status_code, 200)

        assignment = Recommendation.query.filter_by(child_id=self.child_en.id, activity_id=act.id).first()
        self.assertIsNotNone(assignment)

        # 3.7 Teacher Assignments Hub
        res = self.client.get('/teacher/assignments')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Leo English', res.data)

    # -------------------------------------------------------------
    # 4. Admin Journey Tests
    # -------------------------------------------------------------
    def test_admin_journey(self):
        """Audit admin lifecycle: dashboard, users, categories CRUD, activities CRUD, AI draft, audit logs, Action Center, System Agents, Assistant chat, pipeline trigger."""
        # 4.1 Login
        res = self._login('admin@childinsight.test', 'AdminPass123!')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Admin Console', res.data)

        # 4.2 Dashboard
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)

        # 4.3 Users Directory
        res = self.client.get('/admin/users')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Parent Alice', res.data)
        self.assertIn(b'Teacher Davis', res.data)

        # User Toggle Status
        res = self.client.post(f'/admin/users/{self.parent2.id}/toggle-status', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        p2 = db.session.get(User, self.parent2.id)
        self.assertFalse(p2.is_active)
        # Restore
        self.client.post(f'/admin/users/{self.parent2.id}/toggle-status', follow_redirects=True)

        # 4.4 Categories Directory & Create
        res = self.client.get('/admin/categories')
        self.assertEqual(res.status_code, 200)

        res = self.client.post('/admin/categories/new', data={
            'name': 'Music & Rhythm',
            'description': 'Auditory pattern recognition and musical beats.',
            'icon': 'music'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        new_cat = Category.query.filter_by(name='Music & Rhythm').first()
        self.assertIsNotNone(new_cat)

        # 4.5 Activities Directory & Create
        res = self.client.get('/admin/activities')
        self.assertEqual(res.status_code, 200)

        res = self.client.post('/admin/activities/new', data={
            'title': 'Rhythm Clap Beat 1',
            'description': 'Listen to the rhythm and identify the missing beat.',
            'category_id': new_cat.id,
            'difficulty': 'Easy',
            'min_age': 5,
            'max_age': 9,
            'estimated_duration': 8,
            'is_active': 'y'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        new_act = Activity.query.filter_by(title='Rhythm Clap Beat 1').first()
        self.assertIsNotNone(new_act)

        # 4.6 AI Draft Form
        res = self.client.get('/admin/activities/ai-draft')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'AI Content Drafting', res.data)

        # 4.7 Audit Logs
        res = self.client.get('/admin/audit-logs')
        self.assertEqual(res.status_code, 200)

        # 4.8 Action Center
        res = self.client.get('/admin/action-center')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Action Center', res.data)
        self.assertIn(b'admin-assistant-panel', res.data)

        # 4.9 System Agents
        res = self.client.get('/admin/agents')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'System Agents', res.data)
        # Should not have assistant panel
        self.assertNotIn(b'admin-assistant-panel', res.data)

        # 4.10 Admin Assistant - English
        chat_res = self.client.post('/admin/assistant/chat', json={'question': 'How many registered teachers do we have?'})
        self.assertEqual(chat_res.status_code, 200)
        ans = chat_res.get_json()
        self.assertIn('teacher', ans['answer'].lower())

        # 4.11 Admin Assistant - Hindi
        chat_hi_res = self.client.post('/admin/assistant/chat', json={'question': 'सिस्टम में कितने शिक्षक हैं?'})
        self.assertEqual(chat_hi_res.status_code, 200)
        ans_hi = chat_hi_res.get_json()
        self.assertTrue(bool(re.search(r'[\u0900-\u097F]', ans_hi['answer'])))

        # 4.12 Run Agent Scheduler
        run_res = self.client.post('/admin/agents/run', follow_redirects=True)
        self.assertEqual(run_res.status_code, 200)
        self.assertIn(b'Agent pipeline executed successfully', run_res.data)

    # -------------------------------------------------------------
    # 5. Access Control Matrix & Security
    # -------------------------------------------------------------
    def test_access_control_matrix(self):
        """Audit strict RBAC enforcement across roles and unauthenticated requests."""
        admin_urls = [
            '/admin/dashboard', '/admin/users', '/admin/categories', '/admin/activities',
            '/admin/action-center', '/admin/agents', '/admin/audit-logs', '/admin/categories/new'
        ]

        # 5.1 Unauthenticated requests redirect to login
        self._logout()
        for url in ['/admin/dashboard', '/parent/dashboard', '/teacher/dashboard', f'/child/{self.child_en.id}/activities']:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/login', res.headers.get('Location', ''))

        # 5.2 Parent is blocked from all Admin URLs with 403
        self._login('alice@childinsight.test', 'ParentPass123!')
        for url in admin_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 403, f"Parent accessed {url} but expected 403!")

        # Parent is blocked from another parent's child (Bob's child)
        res = self.client.get(f'/parent/children/{self.child_other.id}/edit')
        self.assertEqual(res.status_code, 403)
        res = self.client.get(f'/child/{self.child_other.id}/activities')
        self.assertEqual(res.status_code, 403)

        # 5.3 Teacher is blocked from all Admin URLs with 403
        self._logout()
        self._login('davis@childinsight.test', 'TeacherPass123!')
        for url in admin_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 403, f"Teacher accessed {url} but expected 403!")

        # Teacher is blocked from unassigned child (Bob's child)
        res = self.client.get(f'/teacher/students/{self.child_other.id}')
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()
