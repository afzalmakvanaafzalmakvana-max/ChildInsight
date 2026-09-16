import unittest
from datetime import datetime, timezone
from app import create_app, db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Category, Activity, ActivityQuestion
from app.models.session import ActivitySession, InteractionEvent
from app.models.teacher_assignment import TeacherAssignment
from app.models.recommendation import Recommendation
from app.models.notification import Notification
from app.services import event_tracker, recommendation_service, notification_service


class NotificationSystemTestCase(unittest.TestCase):
    """Automated tests for the In-Dashboard Notification System."""

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # 1. Create Parents
        self.parent1 = User(name='Jordan Smith', email='jordan@example.com', role='parent', is_active=True)
        self.parent1.set_password('Password123')
        self.parent2 = User(name='Taylor Reed', email='taylor@example.com', role='parent', is_active=True)
        self.parent2.set_password('Password123')

        # 2. Create Teacher
        self.teacher = User(name='Maya Lin', email='maya@example.com', role='teacher', is_active=True)
        self.teacher.set_password('Password123')

        db.session.add_all([self.parent1, self.parent2, self.teacher])
        db.session.commit()

        # 3. Create Children
        self.child1 = Child(name='Aarav Smith', age=6, grade='1st', parent_id=self.parent1.id)
        self.child2 = Child(name='Elena Reed', age=7, grade='2nd', parent_id=self.parent2.id)
        db.session.add_all([self.child1, self.child2])
        db.session.commit()

        # 4. Teacher Assignment
        assign = TeacherAssignment(teacher_id=self.teacher.id, child_id=self.child1.id)
        db.session.add(assign)

        # 5. Categories & Activities
        self.cat_memory = Category(name='Memory', slug='memory', description='Memory games')
        self.cat_visual = Category(name='Visual Matching', slug='visual', description='Visual recognition')
        self.cat_reading = Category(name='Interactive Reading', slug='language', description='Language practice')
        db.session.add_all([self.cat_memory, self.cat_visual, self.cat_reading])
        db.session.commit()

        self.act_memory = Activity(category_id=self.cat_memory.id, title='Memory Match', difficulty='Easy', is_active=True)
        self.act_visual = Activity(category_id=self.cat_visual.id, title='Shape Patterns', difficulty='Easy', is_active=True)
        self.act_reading = Activity(category_id=self.cat_reading.id, title='Word Builders', difficulty='Easy', is_active=True)
        db.session.add_all([self.act_memory, self.act_visual, self.act_reading])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email, password='Password123'):
        return self.client.post('/login', data={'email': email, 'password': password})

    def test_notification_model_and_creation(self):
        """Verify Notification model fields, serialization, and relationship defaults."""
        notif = Notification(
            user_id=self.parent1.id,
            child_id=self.child1.id,
            notification_type=Notification.TYPE_GENERAL,
            message='Test welcome notification',
            link='/parent/dashboard'
        )
        db.session.add(notif)
        db.session.commit()

        self.assertIsNotNone(notif.id)
        self.assertFalse(notif.is_read)
        self.assertIsNotNone(notif.created_at)

        data = notif.to_dict()
        self.assertEqual(data['user_id'], self.parent1.id)
        self.assertEqual(data['child_id'], self.child1.id)
        self.assertEqual(data['child_name'], 'Aarav Smith')
        self.assertEqual(data['message'], 'Test welcome notification')
        self.assertFalse(data['is_read'])

    def test_notification_created_on_activity_completion(self):
        """Verify notification is created automatically when a child completes an activity."""
        # Start a session
        act_session = event_tracker.start_session(child_id=self.child1.id, activity_id=self.act_memory.id)
        # Record answers
        event_tracker.record_answer(act_session.id, self.child1.id, question_id=1, selected_answer='Match', is_correct=True)
        
        # Complete session
        completed_session = event_tracker.complete_session(act_session.id, self.child1.id)
        self.assertIsNotNone(completed_session)

        # Verify parent received notification
        parent_notifs = Notification.query.filter_by(user_id=self.parent1.id).all()
        self.assertEqual(len(parent_notifs), 1)
        self.assertEqual(parent_notifs[0].child_id, self.child1.id)
        self.assertEqual(parent_notifs[0].notification_type, Notification.TYPE_ACTIVITY_COMPLETED)
        self.assertIn('Aarav', parent_notifs[0].message)

        # Verify assigned teacher also received notification
        teacher_notifs = Notification.query.filter_by(user_id=self.teacher.id).all()
        self.assertEqual(len(teacher_notifs), 1)
        self.assertEqual(teacher_notifs[0].child_id, self.child1.id)

        # Verify unassigned parent received no notification
        parent2_notifs = Notification.query.filter_by(user_id=self.parent2.id).all()
        self.assertEqual(len(parent2_notifs), 0)

    def test_notification_text_specificity_from_real_data(self):
        """
        Verify notification text is friendly, specific, and constructed from real session data:
        e.g. 'Aarav completed 2 activities today. Strong performance: Memory. Suggested practice: ...'
        """
        # Session 1: High accuracy in Memory (100%)
        s1 = event_tracker.start_session(child_id=self.child1.id, activity_id=self.act_memory.id)
        event_tracker.record_answer(s1.id, self.child1.id, question_id=1, selected_answer='Match', is_correct=True)
        event_tracker.complete_session(s1.id, self.child1.id)

        # Session 2: Lower accuracy in Visual (50%)
        s2 = event_tracker.start_session(child_id=self.child1.id, activity_id=self.act_visual.id)
        event_tracker.record_answer(s2.id, self.child1.id, question_id=1, selected_answer='Shape', is_correct=True)
        event_tracker.record_answer(s2.id, self.child1.id, question_id=2, selected_answer='Wrong', is_correct=False)
        event_tracker.complete_session(s2.id, self.child1.id)

        # Inspect latest notification for parent
        latest_notif = Notification.query.filter_by(user_id=self.parent1.id).order_by(Notification.id.desc()).first()
        self.assertIsNotNone(latest_notif)
        msg = latest_notif.message

        # Verify real-data details
        self.assertIn('Aarav completed 2 activities today', msg)
        self.assertIn('Strong performance: Memory', msg)

    def test_notification_created_on_recommendation_generation(self):
        """Verify notification is created when tailored recommendations are generated."""
        recs = recommendation_service.generate_personalized_recommendations(self.child1.id, persist=True)
        self.assertTrue(len(recs) > 0)

        notif = Notification.query.filter_by(
            user_id=self.parent1.id,
            notification_type=Notification.TYPE_RECOMMENDATION_GENERATED
        ).first()

        self.assertIsNotNone(notif)
        self.assertIn('New learning recommendation for Aarav', notif.message)
        self.assertIn('#recommendations', notif.link)

    def test_notification_created_on_teacher_assignment(self):
        """Verify notification is generated for parent when teacher assigns an activity."""
        self._login(self.teacher.email)

        response = self.client.post(f'/teacher/students/{self.child1.id}/assign-activity', data={
            'activity_id': self.act_reading.id,
            'note': 'Let us work on vocabulary!'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Parent should have notification
        notif = Notification.query.filter_by(
            user_id=self.parent1.id,
            notification_type=Notification.TYPE_TEACHER_ASSIGNED
        ).first()

        self.assertIsNotNone(notif)
        self.assertIn('Educator Maya Lin assigned', notif.message)
        self.assertIn('Word Builders', notif.message)
        self.assertIn('Let us work on vocabulary!', notif.message)

    def test_unread_count_and_marking_as_read(self):
        """Verify unread count tracking and single / bulk mark as read API behavior."""
        # Create 3 notifications for parent1
        n1 = Notification(user_id=self.parent1.id, message='Notice 1')
        n2 = Notification(user_id=self.parent1.id, message='Notice 2')
        n3 = Notification(user_id=self.parent1.id, message='Notice 3')
        db.session.add_all([n1, n2, n3])
        db.session.commit()

        self._login(self.parent1.email)

        # 1. Check initial count
        res = self.client.get('/api/notifications')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['unread_count'], 3)
        self.assertEqual(len(data['notifications']), 3)

        # 2. Mark one notification as read
        res_read = self.client.post(f'/api/notifications/{n1.id}/read')
        self.assertEqual(res_read.status_code, 200)
        data_read = res_read.get_json()
        self.assertTrue(data_read['success'])
        self.assertEqual(data_read['unread_count'], 2)

        db.session.refresh(n1)
        self.assertTrue(n1.is_read)

        # 3. Mark all as read
        res_all = self.client.post('/api/notifications/mark-all-read')
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.get_json()
        self.assertTrue(data_all['success'])
        self.assertEqual(data_all['unread_count'], 0)

        db.session.refresh(n2)
        db.session.refresh(n3)
        self.assertTrue(n2.is_read)
        self.assertTrue(n3.is_read)

    def test_parent_isolation_enforced(self):
        """Verify a parent only sees and can only mutate their own notifications."""
        # Notification for parent1
        n1 = Notification(user_id=self.parent1.id, message='Private message for Jordan')
        # Notification for parent2
        n2 = Notification(user_id=self.parent2.id, message='Private message for Taylor')
        db.session.add_all([n1, n2])
        db.session.commit()

        # Login as Parent 2
        self._login(self.parent2.email)

        # Parent 2 queries list
        res = self.client.get('/api/notifications')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['unread_count'], 1)
        self.assertEqual(len(data['notifications']), 1)
        self.assertEqual(data['notifications'][0]['message'], 'Private message for Taylor')

        # Parent 2 attempts to mark Parent 1's notification as read
        res_hack = self.client.post(f'/api/notifications/{n1.id}/read')
        self.assertEqual(res_hack.status_code, 404)

        db.session.refresh(n1)
        self.assertFalse(n1.is_read)


if __name__ == '__main__':
    unittest.main()
