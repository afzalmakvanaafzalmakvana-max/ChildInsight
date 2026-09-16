import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity
from app.models.session import ActivitySession
from app.models.teacher_assignment import TeacherAssignment
from app.utils.seed_data import seed_activities
from app.services import report_service, analytics_service


class Phase8DashboardsAndReportsTestCase(unittest.TestCase):
    """Automated test suite verifying Phase 8 Dashboards and Reports (Parent/Teacher/Admin, PDF/CSV, ethical safeguards)."""

    FORBIDDEN_RANKING_TERMS = [
        'ranking', 'leaderboard', 'top student', 'worst student',
        'better than', 'worse than', 'rank #', 'versus', 'first place',
        'last place', 'percentile rank', 'class rank'
    ]

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed categories & activities
        seed_activities()
        self.categories = {cat.slug: cat for cat in Category.query.all()}
        self.activities = {cat.slug: Activity.query.filter_by(category_id=cat.id).all() for cat in self.categories.values()}

        # Seed Users
        self.parent_a = User(name='Parent Alice', email='alice@example.com', role='parent')
        self.parent_a.set_password('Pass123!')

        self.parent_b = User(name='Parent Bob', email='bob@example.com', role='parent')
        self.parent_b.set_password('Pass123!')

        self.teacher_1 = User(name='Teacher Taylor', email='taylor@example.com', role='teacher')
        self.teacher_1.set_password('Pass123!')

        self.teacher_2 = User(name='Teacher Morgan', email='morgan@example.com', role='teacher')
        self.teacher_2.set_password('Pass123!')

        self.admin = User(name='Platform Admin', email='admin@example.com', role='admin')
        self.admin.set_password('Pass123!')

        db.session.add_all([self.parent_a, self.parent_b, self.teacher_1, self.teacher_2, self.admin])
        db.session.commit()

        # Seed Children
        self.child_a1 = Child(parent_id=self.parent_a.id, name='Tommy A1', age=6, grade='1st Grade', preferred_language='English')
        self.child_a2 = Child(parent_id=self.parent_a.id, name='Tina A2', age=8, grade='3rd Grade', preferred_language='English')
        self.child_b1 = Child(parent_id=self.parent_b.id, name='Ben B1', age=7, grade='2nd Grade', preferred_language='English')
        db.session.add_all([self.child_a1, self.child_a2, self.child_b1])
        db.session.commit()

        # Assign Child A1 and Child B1 to Teacher 1
        assign1 = TeacherAssignment(teacher_id=self.teacher_1.id, child_id=self.child_a1.id)
        assign2 = TeacherAssignment(teacher_id=self.teacher_1.id, child_id=self.child_b1.id)
        db.session.add_all([assign1, assign2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Pass123!'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def _create_completed_session(self, child_id, activity, accuracy=85.0, attempts=4):
        correct = int(round((accuracy / 100.0) * attempts))
        session = ActivitySession(
            child_id=child_id,
            activity_id=activity.id,
            attempts=attempts,
            correct_answers=correct,
            accuracy=accuracy,
            duration_seconds=90,
            status=ActivitySession.STATUS_COMPLETED
        )
        db.session.add(session)
        db.session.commit()
        return session

    # --- 1. Parent Dashboard Authorization & Isolation ---

    def test_parent_dashboard_authorization_and_ownership(self):
        """Parent dashboard displays only the parent's registered children."""
        self._login('alice@example.com')
        resp = self.client.get('/parent/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Alice's children should be present
        self.assertIn("Tommy A1", html)
        self.assertIn("Tina A2", html)

        # Bob's child must NOT be present
        self.assertNotIn("Ben B1", html)

    def test_parent_cannot_view_unowned_child_profile_or_reports(self):
        """Parent A cannot view Parent B's child profile or download reports (receives 403)."""
        self._login('alice@example.com')

        # Attempt to access Bob's child detail
        resp_detail = self.client.get(f'/parent/children/{self.child_b1.id}')
        self.assertEqual(resp_detail.status_code, 403)

        # Attempt to download Bob's child reports
        resp_pdf = self.client.get(f'/parent/children/{self.child_b1.id}/report/pdf')
        self.assertEqual(resp_pdf.status_code, 403)

        resp_csv = self.client.get(f'/parent/children/{self.child_b1.id}/report/csv')
        self.assertEqual(resp_csv.status_code, 403)

    # --- 2. Teacher Dashboard Ethical Safeguards: Zero Rankings ---

    def test_teacher_dashboard_zero_cross_student_rankings(self):
        """Teacher dashboard must strictly never display rank or score comparisons between students."""
        # Create sessions with different scores for both students
        self._create_completed_session(self.child_a1.id, self.activities['visual'][0], accuracy=95.0)
        self._create_completed_session(self.child_b1.id, self.activities['visual'][0], accuracy=45.0)

        self._login('taylor@example.com')
        resp = self.client.get('/teacher/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True).lower()

        # Both assigned students appear
        self.assertIn("tommy a1", html)
        self.assertIn("ben b1", html)

        # Strictly assert absence of comparative ranking vocabulary
        for forbidden in self.FORBIDDEN_RANKING_TERMS:
            self.assertNotIn(
                forbidden,
                html,
                f"Forbidden comparative term '{forbidden}' found in Teacher Dashboard HTML!"
            )

    def test_teacher_dashboard_individual_progress_badges(self):
        """Teacher dashboard renders individual growth status badges (Progress ↑ / Stable / Practice Suggested / New Learner)."""
        # Tommy A1: High accuracy (90%) -> Progress ↑
        self._create_completed_session(self.child_a1.id, self.activities['visual'][0], accuracy=90.0)

        # Ben B1: Low accuracy (25%) -> Practice Suggested
        self._create_completed_session(self.child_b1.id, self.activities['visual'][0], accuracy=25.0, attempts=4)

        self._login('taylor@example.com')
        resp = self.client.get('/teacher/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn("Progress ↑", html)
        self.assertIn("Practice Suggested", html)

    def test_teacher_access_control_for_assigned_vs_unassigned_students(self):
        """Teacher Morgan (not assigned to Tommy A1) receives 403 when trying to access student profile or report."""
        self._login('morgan@example.com')

        resp_detail = self.client.get(f'/teacher/students/{self.child_a1.id}')
        self.assertEqual(resp_detail.status_code, 403)

        resp_pdf = self.client.get(f'/teacher/students/{self.child_a1.id}/report/pdf')
        self.assertEqual(resp_pdf.status_code, 403)

    # --- 3. Admin Dashboard System Overview ---

    def test_admin_dashboard_system_overview_counts(self):
        """Admin dashboard displays complete platform overview counts and operational links."""
        self._create_completed_session(self.child_a1.id, self.activities['visual'][0], accuracy=80.0)

        self._login('admin@example.com')
        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn("Platform Administration", html)
        self.assertIn("Educational Activities", html)
        self.assertIn("Completed Sessions", html)
        self.assertIn("Manage Users", html)
        self.assertIn("Manage Assignments", html)

    # --- 4. Report Generation (PDF & CSV with Responsible-Use Disclaimer) ---

    def test_pdf_report_generation_and_disclaimer(self):
        """PDF report generation produces a valid PDF file containing the child's name and the responsible-use notice."""
        self._create_completed_session(self.child_a1.id, self.activities['visual'][0], accuracy=88.0)

        pdf_bytes = report_service.generate_child_pdf_report(self.child_a1.id, date_range='all')
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 500)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

        # Inspect raw bytes for critical text components
        pdf_text = pdf_bytes.decode('latin1', errors='ignore')
        self.assertIn("Tommy A1", pdf_text)
        self.assertIn("Responsible-Use Notice", pdf_text)
        self.assertIn("does not evaluate, assess", pdf_text)
        self.assertIn("diagnose any medical or psychological condition", pdf_text)

    def test_csv_report_generation_and_disclaimer(self):
        """CSV report generation produces valid comma-separated text containing metrics and the responsible-use disclaimer."""
        self._create_completed_session(self.child_a1.id, self.activities['visual'][0], accuracy=88.0)

        csv_text = report_service.generate_child_csv_report(self.child_a1.id, date_range='all')
        self.assertIsInstance(csv_text, str)
        self.assertGreater(len(csv_text), 100)

        self.assertIn("Tommy A1", csv_text)
        self.assertIn("OVERALL ANALYTICS SUMMARY", csv_text)
        self.assertIn("RESPONSIBLE-USE NOTICE", csv_text)
        self.assertIn("does not evaluate, assess, or diagnose any medical or psychological condition", csv_text)

    # --- 5. Empty States for Learners with No Sessions ---

    def test_empty_states_for_new_learners(self):
        """Children with zero sessions render friendly empty states without crashing."""
        self._login('alice@example.com')
        # Switch to Tina A2 who has zero sessions
        resp = self.client.get(f'/parent/dashboard?child_id={self.child_a2.id}')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn("No activity history yet for Tina A2", html)
        self.assertIn("Open Activity Hub", html)


if __name__ == '__main__':
    unittest.main()
