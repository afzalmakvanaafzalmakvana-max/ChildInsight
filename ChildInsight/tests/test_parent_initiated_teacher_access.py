import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.teacher_assignment import TeacherAssignment
from app.models.child_teacher_access import ChildTeacherAccess
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.activity import Category, Activity
from app.models.session import ActivitySession
from app.utils.seed_data import seed_activities


class ParentInitiatedTeacherAccessTestCase(unittest.TestCase):
    """Automated tests for Parent-Initiated Teacher Access feature and child card direct share button."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed test users
        self.parent_a = User(name='Alice', email='alice@parent.com', role='parent')
        self.parent_a.set_password('Pass123!')

        self.parent_b = User(name='Bob', email='bob@parent.com', role='parent')
        self.parent_b.set_password('Pass123!')

        self.teacher_1 = User(name='Teacher Davis', email='davis@school.org', role='teacher')
        self.teacher_1.set_password('Pass123!')

        self.teacher_2 = User(name='Teacher Miller', email='miller@school.org', role='teacher')
        self.teacher_2.set_password('Pass123!')

        self.inactive_teacher = User(name='Teacher Inactive', email='inactive@school.org', role='teacher', is_active=False)
        self.inactive_teacher.set_password('Pass123!')

        self.admin = User(name='Admin Charlie', email='admin@childinsight.com', role='admin')
        self.admin.set_password('Pass123!')

        db.session.add_all([
            self.parent_a, self.parent_b, self.teacher_1, self.teacher_2,
            self.inactive_teacher, self.admin
        ])
        db.session.commit()

        # Create child for Alice
        self.child_leo = Child(
            parent_id=self.parent_a.id,
            name='Leo',
            age=7,
            grade='2nd Grade',
            preferred_language='English'
        )
        self.child_anzar = Child(
            parent_id=self.parent_a.id,
            name='anzar',
            age=8,
            grade='3rd Grade',
            preferred_language='English'
        )
        self.child_maya = Child(
            parent_id=self.parent_b.id,
            name='Maya',
            age=9,
            grade='4th Grade',
            preferred_language='English'
        )
        db.session.add_all([self.child_leo, self.child_anzar, self.child_maya])
        db.session.commit()

        # Seed activities and a test session for Leo
        seed_activities()
        act = Activity.query.filter_by(is_active=True).first()
        if act:
            session = ActivitySession(
                child_id=self.child_leo.id,
                activity_id=act.id,
                status=ActivitySession.STATUS_COMPLETED,
                accuracy=85.0,
                duration_seconds=120,
                attempts=5,
                correct_answers=4
            )
            db.session.add(session)
            db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Pass123!'):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # --------------------------------------------------------------------------
    # 1. Child Card Direct "Share with Teacher" Button
    # --------------------------------------------------------------------------
    def test_share_with_teacher_button_on_children_list(self):
        """Verify the 'Share with Teacher' button is rendered on each child card (e.g. anzar),
        sits next to 'Edit', uses btn-outline btn-sm styling, wraps cleanly,
        and navigates directly to the correct child's share flow.
        """
        self._login(self.parent_a.email)
        resp = self.client.get('/parent/children')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Confirm both anzar and leo are present
        self.assertIn('anzar', html)
        self.assertIn('Leo', html)

        # Confirm button exists for Leo and Anzar with exact anchors
        leo_share_href = f"/parent/children/{self.child_leo.id}#share-with-teacher"
        anzar_share_href = f"/parent/children/{self.child_anzar.id}#share-with-teacher"
        self.assertIn(leo_share_href, html)
        self.assertIn(anzar_share_href, html)

        # Confirm visual styling and wrapping container
        self.assertIn('Share with Teacher</a>', html)
        self.assertIn('btn-outline btn-sm', html)
        self.assertIn('child-card-actions', html)
        self.assertIn('flex-wrap: wrap;', html)

        # Confirm buttons are structured: View Profile, Edit, Share with Teacher
        self.assertIn(f"/parent/children/{self.child_anzar.id}", html)
        self.assertIn(f"/parent/children/{self.child_anzar.id}/edit", html)

        # Test following the link navigates to the child's detail page and contains the #share-with-teacher card
        detail_resp = self.client.get(f"/parent/children/{self.child_anzar.id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail_html = detail_resp.get_data(as_text=True)
        self.assertIn('id="share-with-teacher"', detail_html)
        self.assertIn('Share with a Teacher', detail_html)
        self.assertIn(f"/parent/children/{self.child_anzar.id}/share-teacher", detail_html)

        # Test direct share route alias
        alias_resp = self.client.get(f"/parent/children/{self.child_anzar.id}/share")
        self.assertEqual(alias_resp.status_code, 302)
        self.assertIn(f"/parent/children/{self.child_anzar.id}", alias_resp.location)
        self.assertIn("share-with-teacher", alias_resp.location)

        alias_followed = self.client.get(f"/parent/children/{self.child_anzar.id}/share", follow_redirects=True)
        self.assertEqual(alias_followed.status_code, 200)
        self.assertIn('id="share-with-teacher"', alias_followed.get_data(as_text=True))

    # --------------------------------------------------------------------------
    # 2. Parent-Initiated Invite Flow (Validation & Security)
    # --------------------------------------------------------------------------
    def test_parent_can_invite_valid_teacher(self):
        """Parent successfully sends access request to a valid, active teacher."""
        self._login(self.parent_a.email)

        resp = self.client.post(
            f"/parent/children/{self.child_leo.id}/share-teacher",
            data={'teacher_email': self.teacher_1.email},
            follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn(f"Access request sent to {self.teacher_1.name}", html)

        # Verify DB entry
        grant = ChildTeacherAccess.query.filter_by(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_1.id
        ).first()
        self.assertIsNotNone(grant)
        self.assertEqual(grant.status, ChildTeacherAccess.STATUS_PENDING_APPROVAL)
        self.assertEqual(grant.requested_by_parent_id, self.parent_a.id)
        self.assertEqual(grant.invited_email, self.teacher_1.email)

        # Verify Audit Log
        audit = AuditLog.query.filter_by(
            action='parent_grant_teacher_access_invite',
            target_id=grant.id
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.parent_a.id)

        # Verify Notification sent to teacher
        notif = Notification.query.filter_by(
            user_id=self.teacher_1.id,
            notification_type='teacher_access_request'
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn(self.parent_a.name, notif.message)
        self.assertIn(self.child_leo.name, notif.message)

    def test_invite_nonexistent_or_non_teacher_email_rejected_safely(self):
        """Non-teacher or unregistered emails are rejected without leaking account existence."""
        self._login(self.parent_a.email)

        # Non-existent email
        resp1 = self.client.post(
            f"/parent/children/{self.child_leo.id}/share-teacher",
            data={'teacher_email': 'nobody@randomdomain.com'},
            follow_redirects=True
        )
        self.assertIn("No active teacher account found with this email", resp1.get_data(as_text=True))

        # Email exists, but is a parent (not teacher)
        resp2 = self.client.post(
            f"/parent/children/{self.child_leo.id}/share-teacher",
            data={'teacher_email': self.parent_b.email},
            follow_redirects=True
        )
        # MUST show the exact same message to prevent enumeration
        self.assertIn("No active teacher account found with this email", resp2.get_data(as_text=True))

        # Email exists, but teacher is inactive
        resp3 = self.client.post(
            f"/parent/children/{self.child_leo.id}/share-teacher",
            data={'teacher_email': self.inactive_teacher.email},
            follow_redirects=True
        )
        self.assertIn("No active teacher account found with this email", resp3.get_data(as_text=True))

        # Zero records created
        self.assertEqual(ChildTeacherAccess.query.count(), 0)

    def test_anti_spam_duplicate_invite_blocked(self):
        """Cannot send duplicate pending requests for the same child-teacher pair."""
        self._login(self.parent_a.email)

        # First request
        self.client.post(
            f"/parent/children/{self.child_leo.id}/share-teacher",
            data={'teacher_email': self.teacher_1.email},
            follow_redirects=True
        )

        # Second request
        resp = self.client.post(
            f"/parent/children/{self.child_leo.id}/share-teacher",
            data={'teacher_email': self.teacher_1.email},
            follow_redirects=True
        )
        self.assertIn("already pending approval", resp.get_data(as_text=True))
        self.assertEqual(ChildTeacherAccess.query.count(), 1)

    # --------------------------------------------------------------------------
    # 3. Teacher Accept and Decline Flows
    # --------------------------------------------------------------------------
    def test_teacher_sees_pending_request_and_can_accept(self):
        """Teacher sees pending request on dashboard and can accept it."""
        # Create pending grant
        grant = ChildTeacherAccess(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_1.id,
            invited_email=self.teacher_1.email,
            status=ChildTeacherAccess.STATUS_PENDING_APPROVAL,
            requested_by_parent_id=self.parent_a.id
        )
        db.session.add(grant)
        db.session.commit()

        # Login as teacher
        self._login(self.teacher_1.email)
        dash_resp = self.client.get('/teacher/dashboard')
        self.assertEqual(dash_resp.status_code, 200)
        html = dash_resp.get_data(as_text=True)
        self.assertIn("Pending Student Access Requests", html)
        self.assertTrue(
            f"Parent {self.parent_a.name} has requested you view {self.child_leo.name}'s report" in html or
            f"Parent {self.parent_a.name} has requested you view {self.child_leo.name}&#39;s report" in html
        )
        self.assertIn(f"/teacher/access-requests/{grant.id}/accept", html)
        self.assertIn(f"/teacher/access-requests/{grant.id}/decline", html)

        # Accept request
        accept_resp = self.client.post(f"/teacher/access-requests/{grant.id}/accept", follow_redirects=True)
        self.assertEqual(accept_resp.status_code, 200)
        self.assertIn("Access granted for Leo", accept_resp.get_data(as_text=True))

        # Verify DB status
        db.session.refresh(grant)
        self.assertEqual(grant.status, ChildTeacherAccess.STATUS_ACTIVE)
        self.assertIsNotNone(grant.responded_at)

        # Verify Audit Log
        audit = AuditLog.query.filter_by(
            action='teacher_accept_access_request',
            target_id=grant.id
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.teacher_1.id)

        # Verify Notification to parent
        notif = Notification.query.filter_by(
            user_id=self.parent_a.id,
            notification_type='teacher_access_accepted'
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn(self.teacher_1.name, notif.message)
        self.assertIn(self.child_leo.name, notif.message)

    def test_teacher_can_decline_access_request(self):
        """Teacher can decline access request; parent is notified and teacher gains no access."""
        grant = ChildTeacherAccess(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_1.id,
            invited_email=self.teacher_1.email,
            status=ChildTeacherAccess.STATUS_PENDING_APPROVAL,
            requested_by_parent_id=self.parent_a.id
        )
        db.session.add(grant)
        db.session.commit()

        self._login(self.teacher_1.email)
        decline_resp = self.client.post(f"/teacher/access-requests/{grant.id}/decline", follow_redirects=True)
        self.assertEqual(decline_resp.status_code, 200)
        self.assertIn("Access request for Leo declined", decline_resp.get_data(as_text=True))

        db.session.refresh(grant)
        self.assertEqual(grant.status, ChildTeacherAccess.STATUS_DECLINED)
        self.assertIsNotNone(grant.responded_at)

        # Verify audit log
        audit = AuditLog.query.filter_by(
            action='teacher_decline_access_request',
            target_id=grant.id
        ).first()
        self.assertIsNotNone(audit)

        # Verify parent notification
        notif = Notification.query.filter_by(
            user_id=self.parent_a.id,
            notification_type='teacher_access_declined'
        ).first()
        self.assertIsNotNone(notif)

        # Verify teacher cannot access child
        resp = self.client.get(f"/teacher/students/{self.child_leo.id}")
        self.assertEqual(resp.status_code, 403)

    # --------------------------------------------------------------------------
    # 4. Access Control Verification (Reports, Analytics, Decorators)
    # --------------------------------------------------------------------------
    def test_accepted_teacher_can_view_full_reports_and_analytics(self):
        """Teacher with active parent grant can view full student detail, reports, and API."""
        grant = ChildTeacherAccess(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_1.id,
            invited_email=self.teacher_1.email,
            status=ChildTeacherAccess.STATUS_ACTIVE,
            requested_by_parent_id=self.parent_a.id,
            responded_at=datetime.now(timezone.utc)
        )
        db.session.add(grant)
        db.session.commit()

        # Login as teacher_1
        self._login(self.teacher_1.email)

        # 1. Student detail page
        detail_resp = self.client.get(f"/teacher/students/{self.child_leo.id}")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertIn("Leo", detail_resp.get_data(as_text=True))

        # 2. PDF Report download
        pdf_resp = self.client.get(f"/teacher/students/{self.child_leo.id}/report/pdf")
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp.mimetype, 'application/pdf')

        # 3. CSV Report download
        csv_resp = self.client.get(f"/teacher/students/{self.child_leo.id}/report/csv")
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("text/csv", csv_resp.mimetype)

        # 4. REST API check
        api_resp = self.client.get(f"/api/children/{self.child_leo.id}")
        self.assertEqual(api_resp.status_code, 200)

        # 5. Teacher roster lists child
        roster_resp = self.client.get('/teacher/students')
        self.assertIn("Leo", roster_resp.get_data(as_text=True))

    def test_unassigned_unaccepted_teacher_blocked(self):
        """Teacher with neither admin assignment nor active parent grant is blocked (403)."""
        self._login(self.teacher_2.email)

        # Attempt to view Leo
        resp = self.client.get(f"/teacher/students/{self.child_leo.id}")
        self.assertEqual(resp.status_code, 403)

        # Attempt to download PDF
        pdf_resp = self.client.get(f"/teacher/students/{self.child_leo.id}/report/pdf")
        self.assertEqual(pdf_resp.status_code, 403)

        # Attempt API access
        api_resp = self.client.get(f"/api/children/{self.child_leo.id}")
        self.assertEqual(api_resp.status_code, 403)

    def test_parent_revoke_immediately_terminates_access(self):
        """Parent revoking access immediately blocks teacher with 403."""
        grant = ChildTeacherAccess(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_1.id,
            invited_email=self.teacher_1.email,
            status=ChildTeacherAccess.STATUS_ACTIVE,
            requested_by_parent_id=self.parent_a.id,
            responded_at=datetime.now(timezone.utc)
        )
        db.session.add(grant)
        db.session.commit()

        # Teacher can access before revoke
        self._login(self.teacher_1.email)
        self.assertEqual(self.client.get(f"/teacher/students/{self.child_leo.id}").status_code, 200)

        # Parent logs in and revokes
        self._login(self.parent_a.email)
        revoke_resp = self.client.post(
            f"/parent/children/{self.child_leo.id}/teacher-access/{grant.id}/revoke",
            follow_redirects=True
        )
        self.assertEqual(revoke_resp.status_code, 200)
        self.assertIn(f"Access for {self.teacher_1.name} has been revoked", revoke_resp.get_data(as_text=True))

        db.session.refresh(grant)
        self.assertEqual(grant.status, ChildTeacherAccess.STATUS_REVOKED)
        self.assertIsNotNone(grant.revoked_at)

        # Teacher immediately loses access (403)
        self._login(self.teacher_1.email)
        self.assertEqual(self.client.get(f"/teacher/students/{self.child_leo.id}").status_code, 403)
        self.assertEqual(self.client.get(f"/teacher/students/{self.child_leo.id}/report/pdf").status_code, 403)
        self.assertEqual(self.client.get(f"/api/children/{self.child_leo.id}").status_code, 403)

    # --------------------------------------------------------------------------
    # 5. Multiple Educators Supported
    # --------------------------------------------------------------------------
    def test_multiple_active_teachers_supported_for_same_child(self):
        """A child can have multiple teachers granted access simultaneously without artificial limits."""
        grant1 = ChildTeacherAccess(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_1.id,
            invited_email=self.teacher_1.email,
            status=ChildTeacherAccess.STATUS_ACTIVE,
            requested_by_parent_id=self.parent_a.id
        )
        grant2 = ChildTeacherAccess(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_2.id,
            invited_email=self.teacher_2.email,
            status=ChildTeacherAccess.STATUS_ACTIVE,
            requested_by_parent_id=self.parent_a.id
        )
        db.session.add_all([grant1, grant2])
        db.session.commit()

        # Both teachers can view Leo
        self._login(self.teacher_1.email)
        self.assertEqual(self.client.get(f"/teacher/students/{self.child_leo.id}").status_code, 200)

        self._login(self.teacher_2.email)
        self.assertEqual(self.client.get(f"/teacher/students/{self.child_leo.id}").status_code, 200)

    # --------------------------------------------------------------------------
    # 6. Admin Oversight & Revocation
    # --------------------------------------------------------------------------
    def test_admin_oversight_and_revoke(self):
        """Admin can view parent-granted access list and can revoke any grant with audit logging."""
        grant = ChildTeacherAccess(
            child_id=self.child_leo.id,
            teacher_id=self.teacher_1.id,
            invited_email=self.teacher_1.email,
            status=ChildTeacherAccess.STATUS_ACTIVE,
            requested_by_parent_id=self.parent_a.id
        )
        db.session.add(grant)
        db.session.commit()

        self._login(self.admin.email)

        # Admin views assignments page with parent-grants section
        resp = self.client.get('/admin/assignments')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Parent-Granted Educator Access", html)
        self.assertIn(self.teacher_1.name, html)
        self.assertIn(self.child_leo.name, html)

        # Admin revokes grant
        revoke_resp = self.client.post(f"/admin/teacher-access/{grant.id}/revoke", follow_redirects=True)
        self.assertEqual(revoke_resp.status_code, 200)
        self.assertIn("revoked by admin", revoke_resp.get_data(as_text=True))

        db.session.refresh(grant)
        self.assertEqual(grant.status, ChildTeacherAccess.STATUS_REVOKED)

        # Verify audit log
        audit = AuditLog.query.filter_by(
            action='admin_revoke_parent_teacher_access',
            target_id=grant.id
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.admin.id)

        # Teacher immediately loses access
        self._login(self.teacher_1.email)
        self.assertEqual(self.client.get(f"/teacher/students/{self.child_leo.id}").status_code, 403)


if __name__ == '__main__':
    unittest.main()
